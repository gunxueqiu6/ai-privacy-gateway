"""
脱敏引擎模块 - 正则表达式脱敏引擎
支持 NER 命名实体识别，覆盖 13 种实体类型
"""

import re
import hashlib
import json
import os
import threading
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Dict, List, Optional, Any

logger = logging.getLogger(__name__)

try:
    from ner_engine import get_ner_engine, NEREntityType

    HAS_NER = True
except ImportError:
    HAS_NER = False
    logger.warning("NER engine not available, using regex only")


# 基础实体类型（catalog 缺失时的回退白名单）
_FALLBACK_ENTITY_TYPES = frozenset(
    {
        "phone",
        "email",
        "idcard",
        "bankcard",
        "plate",
        "coordinates",
        "ip",
        "url",
        "date",
        "amount",
        "postcode",
        "passport",
        "ssn",
        "credit_code",
        "mac",
        "api_key",
        "person",
        "location",
        "organization",
        "custom",
    }
)


def _load_entity_catalog() -> Optional[Dict[str, Any]]:
    """从 entity_catalog.json 加载实体目录（数据驱动）。

    目录缺失或损坏时返回 None，引擎回退到内置 BUILTIN_RULES。
    """
    path = os.environ.get("ENTITY_CATALOG_PATH", "./entity_catalog.json")
    if not os.path.exists(path):
        logger.warning("实体目录不存在: %s，使用内置回退规则", path)
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        entities = data.get("entities", [])
        return {e["key"]: e for e in entities if isinstance(e, dict) and e.get("key")}
    except Exception as e:
        logger.warning("加载实体目录失败: %s，使用内置回退规则", e)
        return None


ENTITY_CATALOG: Optional[Dict[str, Any]] = _load_entity_catalog()

KNOWN_ENTITY_TYPES = (
    frozenset(ENTITY_CATALOG.keys()) if ENTITY_CATALOG else _FALLBACK_ENTITY_TYPES
)


# NER 引擎返回的实体类型缩写 → 目录 key 的映射
_NER_TYPE_TO_KEY = {
    "PER": "person",
    "LOC": "location",
    "ORG": "organization",
    "PHONE": "phone",
    "EMAIL": "email",
    "IDCARD": "idcard",
    "BANKCARD": "bankcard",
    "PLATE": "plate",
    "IP": "ip",
    "URL": "url",
    "DATE": "date",
    "AMOUNT": "amount",
    "POSTCODE": "postcode",
    "APIKEY": "api_key",
}


class AhoCorasickAutomaton:
    """Aho-Corasick 多模式匹配自动机

    支持多关键词同时搜索，一次遍历文本即可找出所有匹配。
    返回结果按匹配长度降序排列（最长匹配优先）。
    仅使用 Python 标准库实现，无需外部依赖。
    """

    class _Node:
        """Trie 节点"""

        __slots__ = ("children", "fail", "output")

        def __init__(self):
            self.children = {}
            self.fail = None
            self.output = []

    def __init__(self):
        self._root = self._Node()
        self._built = False
        self._word_count = 0

    def add_word(self, word: str) -> None:
        """添加关键词到自动机"""
        if not word:
            return
        node = self._root
        for char in word:
            if char not in node.children:
                node.children[char] = self._Node()
            node = node.children[char]
        node.output.append(word)
        self._word_count += 1
        self._built = False

    def _build(self) -> None:
        """构建失败链接（fail pointers）— BFS 层序遍历"""
        from collections import deque

        self._root.fail = self._root
        queue: deque = deque()

        for child in self._root.children.values():
            child.fail = self._root
            queue.append(child)

        while queue:
            current = queue.popleft()
            for char, child in current.children.items():
                queue.append(child)
                fail = current.fail
                while fail is not self._root and char not in fail.children:
                    fail = fail.fail
                child.fail = fail.children.get(char, self._root)
                if child.fail is not self._root:
                    child.output.extend(child.fail.output)

        self._built = True

    def search(self, text: str) -> List[Tuple[int, int, str]]:
        """在文本中搜索所有匹配的关键词

        返回: List[(start, end, word)]，按长度降序排列（最长匹配优先）
        """
        if not self._root.children:
            return []
        if not self._built:
            self._build()

        matches: List[Tuple[int, int, str]] = []
        node = self._root

        for i, char in enumerate(text):
            while node is not self._root and char not in node.children:
                node = node.fail
            node = node.children.get(char, self._root)
            for word in node.output:
                matches.append((i - len(word) + 1, i + 1, word))

        # 去重：同一位置同一关键词只保留一次
        seen: set = set()
        unique: List[Tuple[int, int, str]] = []
        for start, end, word in matches:
            key = (start, word)
            if key not in seen:
                seen.add(key)
                unique.append((start, end, word))

        # 最长匹配优先
        unique.sort(key=lambda x: (-len(x[2]), x[0]))
        return unique


class MaskEngineInterface(ABC):
    """脱敏引擎抽象接口"""

    @abstractmethod
    def mask(self, text: str) -> Tuple[str, Dict[str, str], Dict[str, int]]:
        """
        脱敏处理
        返回: (脱敏后文本, 映射字典, 统计信息)
        """
        pass

    @abstractmethod
    def unmask(self, text: str, mappings: Dict[str, str]) -> str:
        """
        还原处理
        """
        pass

    @abstractmethod
    def add_custom_keyword(self, keyword: str) -> bool:
        """
        添加自定义敏感词
        """
        pass

    @abstractmethod
    def remove_custom_keyword(self, keyword: str) -> bool:
        """
        删除自定义敏感词
        """
        pass

    @abstractmethod
    def get_custom_keywords(self) -> List[str]:
        """
        获取自定义敏感词列表
        """
        pass

    @abstractmethod
    def add_custom_regex_rule(self, name: str, pattern: str, entity_type: str) -> bool:
        """
        添加自定义正则规则
        """
        pass

    @abstractmethod
    def remove_custom_regex_rule(self, name: str) -> bool:
        """
        删除自定义正则规则
        """
        pass

    @abstractmethod
    def get_custom_regex_rules(self) -> List[Dict[str, Any]]:
        """
        获取自定义正则规则列表
        """
        pass

    @abstractmethod
    def toggle_custom_regex_rule(self, name: str, enabled: bool) -> bool:
        """
        启用/禁用自定义正则规则
        """
        pass

    @abstractmethod
    def get_entity_catalog(self) -> List[Dict[str, Any]]:
        """返回数据驱动实体目录（key -> 实体元数据）。"""
        raise NotImplementedError


class RegexMaskEngine(MaskEngineInterface):
    """正则表达式脱敏引擎"""

    # 占位符使用随机序列号标识，无需固定密钥
    _sequence_counter = 0
    _sequence_lock = threading.Lock()

    BUILTIN_RULES = {
        "phone": re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)"),
        "email": re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"),
        "idcard": re.compile(
            r"(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)"
        ),
        "bankcard": re.compile(r"(?<!\d)([1-9]\d{15,18})(?!\d)"),
        "plate": re.compile(
            r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}"
        ),
        # API Key — 20+ known provider formats (OpenAI/Anthropic/GitHub/AWS/Slack/etc.)
        "api_key": re.compile(
            r"\b("
            r"sk-(?:proj-|ant-)?[A-Za-z0-9]{15,}"  # OpenAI project / Anthropic
            r"|gh[pousr]_[A-Za-z0-9]{36,}"  # GitHub personal/OAuth/user/server/refresh tokens
            r"|AKIA[0-9A-Z]{16}"  # AWS IAM access key
            r"|xox[abp]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,}"  # Slack bot/user tokens
            r"|hf_[A-Za-z0-9]{25,}"  # HuggingFace
            r"|glpat-[A-Za-z0-9\-_]{20,}"  # GitLab personal access token
            r"|AIza[0-9A-Za-z\-_]{35}"  # Google API key
            r"|SG\.[A-Za-z0-9\-_]{22,}\.[A-Za-z0-9\-_]{22,}"  # SendGrid
            r"|s[ck]_(?:live|test)_[0-9A-Za-z]{24,}"  # Stripe secret/publishable keys
            r"|rk_(?:live|test)_[0-9A-Za-z]{24,}"  # Stripe restricted keys
            r"|ya29\.[0-9A-Za-z\-_]{50,}"  # Google OAuth access token
            r"|acct[0-9A-Fa-f]{32}"  # Twilio account SID (hex)
            r"|key-[A-Za-z0-9\-_]{20,}"  # Generic API key prefix
            r"|sk-[A-Za-z0-9]{15,}"  # Generic sk- prefix (catch-all)
            r")\b"
        ),
        "coordinates": re.compile(
            r"(?<!\d)(\d{1,3}\.\d{4,}\s*[,，\s]\s*\d{1,3}\.\d{4,})(?!\d)"
        ),
        "ip": re.compile(
            r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
        ),
        "url": re.compile(r"https?://[^\s]+"),
        "date": re.compile(
            r"\d{4}[-/年](?:0?[1-9]|1[0-2])[-/月](?:0?[1-9]|[12]\d|3[01])日?"
        ),
        "amount": re.compile(r"(?:¥|￥|\$)\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?"),
        # 邮编 - 注意：可能误匹配6位连续数字（如订单号、快递单号等）
        "postcode": re.compile(r"(?<!\d)([1-9]\d{5})(?!\d)"),
        "passport": re.compile(r"(?<![A-Z])(E\d{8})(?!\d)"),
        "ssn": re.compile(r"(?<!\d)(\d{3}-\d{2}-\d{4})(?!\d)"),
        "credit_code": re.compile(
            r"(?<![A-Z0-9])([0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10})(?![A-Z0-9])"
        ),
        "mac": re.compile(
            r"(?i)(?<![0-9A-F])([0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2})(?![0-9A-F])"  # noqa: E501
        ),
    }

    ENTITY_TYPE_MAP = {
        "phone": "PII_PHONE",
        "email": "PII_EMAIL",
        "idcard": "PII_IDCARD",
        "bankcard": "PII_BANK",
        "plate": "PII_PLATE",
        "ip": "PII_IP",
        "url": "PII_URL",
        "date": "PII_DATE",
        "amount": "PII_AMOUNT",
        "postcode": "PII_POSTCODE",
        "person": "PII_PER",
        "location": "PII_LOC",
        "organization": "PII_ORG",
        "custom": "PII_CUST",
        "passport": "PII_PASSPORT",
        "ssn": "PII_SSN",
        "credit_code": "PII_CREDIT_CODE",
        "mac": "PII_MAC",
        "coordinates": "PII_COORDINATES",
        "api_key": "PII_APIKEY",
    }

    # 内置规则匹配顺序（specific 优先于 generic；改动需谨慎）。
    # 未在此列表中的 regex 实体按 key 排序追加在末尾。
    BUILTIN_RULE_ORDER = (
        "phone",
        "email",
        "credit_code",
        "idcard",
        "bankcard",
        "plate",
        "coordinates",
        "ip",
        "url",
        "date",
        "api_key",
        "amount",
        "postcode",
        "passport",
        "ssn",
        "mac",
        "hkmo_pass",
        "taiwan_pass",
        "taiwan_id",
        "org_code",
        "hkmo_resident",
        "military_id",
    )

    def __init__(self):
        self.custom_keywords: List[str] = []
        self._automaton = AhoCorasickAutomaton()
        self._custom_regex_rules: Dict[str, Tuple[re.Pattern, str]] = {}
        self._disabled_custom_regex_rules: set = set()
        self._ner_engine = None
        if HAS_NER:
            self._ner_engine = get_ner_engine()

        # 数据驱动实体目录（从 entity_catalog.json 加载，缺失时回退内置规则）
        self._builtin_rules: Dict[str, re.Pattern] = {}
        self._entity_map: Dict[str, str] = {}
        self._entity_meta: Dict[str, Dict[str, Any]] = {}
        self._enabled_entities: set = set()
        self._reload_builtin_rules()

    def _reload_builtin_rules(self) -> None:
        """从 ENTITY_CATALOG 构建内置规则/实体映射/启用开关。"""
        if ENTITY_CATALOG:
            for key, e in ENTITY_CATALOG.items():
                self._entity_meta[key] = e
                self._entity_map[key] = (
                    e.get("placeholder_token") or f"PII_{key.upper()}"
                )
                if e.get("enabled", True):
                    self._enabled_entities.add(key)
                if e.get("detector") == "regex" and e.get("pattern"):
                    try:
                        self._builtin_rules[key] = re.compile(e["pattern"])
                    except re.error as err:
                        logger.warning("实体 '%s' 正则无效，已跳过: %s", key, err)
        else:
            self._builtin_rules = dict(self.BUILTIN_RULES)
            self._entity_map = dict(self.ENTITY_TYPE_MAP)
            self._enabled_entities = set(self.BUILTIN_RULES.keys()) | {
                "person",
                "location",
                "organization",
                "custom",
            }
            for key, token in self._entity_map.items():
                detector = (
                    "ner" if key in ("person", "location", "organization") else "regex"
                )
                self._entity_meta[key] = {
                    "key": key,
                    "placeholder_token": token,
                    "detector": detector,
                    "enabled": True,
                    "compliance_tag": "personal_info",
                }

    @staticmethod
    def _to_alpha_id(n: int) -> str:
        """将正整数转为纯字母 ID（A, B, ..., Z, AA, AB, ...）。

        避免占位符中出现数字，防止 NER/内置规则误匹配占位符内的数字序列。
        """
        result = []
        while n > 0:
            n -= 1
            result.append(chr(ord("A") + (n % 26)))
            n //= 26
        return "".join(reversed(result))

    @staticmethod
    def _luhn_valid(number: str) -> bool:
        """Luhn 校验（银行卡等卡号的校验位验证）。"""
        if not number.isdigit():
            return False
        total = 0
        for i, ch in enumerate(number[::-1]):
            d = int(ch)
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        return total % 10 == 0

    @classmethod
    def _get_next_sequence(cls) -> str:
        with cls._sequence_lock:
            cls._sequence_counter += 1
            return cls._to_alpha_id(cls._sequence_counter)

    def _create_placeholder(self, entity_type: str, value: str) -> str:
        sequence = self._get_next_sequence()
        return f"[PII_{entity_type.upper()}_{sequence}]"

    def _apply_rule(
        self,
        result: str,
        rule_key: str,
        mappings: Dict[str, str],
        stats: Dict[str, int],
        filter_fn=None,
    ) -> str:
        """Apply a single built-in regex rule to the text.

        Uses position-based replacement to avoid over-replacing when
        the same PII value appears multiple times in the text.
        The optional filter_fn(match) should return True to skip the match.
        """
        replacements = []
        for match in self._builtin_rules[rule_key].finditer(result):
            match_str = match.group(0)
            if filter_fn and filter_fn(match_str):
                continue
            placeholder = self._create_placeholder(rule_key, match_str)
            replacements.append((match.start(), match.end(), placeholder, match_str))
            mappings[placeholder] = match_str
            stats[rule_key] += 1
        # Replace from end to start to preserve positions
        for start, end, placeholder, _ in sorted(replacements, key=lambda x: -x[0]):
            result = result[:start] + placeholder + result[end:]
        return result

    def mask(self, text: str) -> Tuple[str, Dict[str, str], Dict[str, int]]:
        """正则脱敏处理 - 支持 13 种实体类型

        处理顺序：自定义关键词优先，确保用户定义的关键词不会被
        NER/内置规则的子串匹配破坏。
        """
        result = text
        mappings: Dict[str, str] = {}
        stats: Dict[str, int] = {key: 0 for key in self._entity_map}

        # 1. 自定义关键词优先处理（使用 Aho-Corasick 自动机，位置替换）
        kw_matches = self._automaton.search(result)
        kw_replacements = []
        for start, end, keyword in kw_matches:
            placeholder = self._create_placeholder("custom", keyword)
            kw_replacements.append((start, end, placeholder, keyword))
            mappings[placeholder] = keyword
            stats["custom"] += 1
        # Replace from end to start to preserve positions
        for start, end, placeholder, _ in sorted(kw_replacements, key=lambda x: -x[0]):
            result = result[:start] + placeholder + result[end:]

        # 2. 自定义正则规则（位置替换）
        for rule_name, (
            compiled_regex,
            entity_type,
        ) in self._custom_regex_rules.items():
            if rule_name in self._disabled_custom_regex_rules:
                continue
            rule_replacements = []
            for match in compiled_regex.finditer(result):
                match_str = match.group(0)
                placeholder = self._create_placeholder(entity_type, match_str)
                rule_replacements.append(
                    (match.start(), match.end(), placeholder, match_str)
                )
                mappings[placeholder] = match_str
                if entity_type in stats:
                    stats[entity_type] += 1
            for start, end, placeholder, _ in sorted(
                rule_replacements, key=lambda x: -x[0]
            ):
                result = result[:start] + placeholder + result[end:]

        # 3. NER 引擎检测人名、地名、机构名
        if self._ner_engine:
            entities = self._ner_engine.detect(result)
            for entity in entities:
                entity_type = _NER_TYPE_TO_KEY.get(
                    entity.entity_type.value, entity.entity_type.value.lower()
                )
                if entity_type in stats and entity_type in self._enabled_entities:
                    placeholder = self._create_placeholder(entity_type, entity.value)
                    result = result.replace(entity.value, placeholder)
                    mappings[placeholder] = entity.value
                    stats[entity_type] += 1

        # 4. 内置规则（按 BUILTIN_RULE_ORDER 顺序，specific 优先；银行卡需跳过11位手机号并做 Luhn 校验）
        def _bankcard_filter(m: str) -> bool:
            if len(m) == 11 and m.startswith("1"):
                return True  # 跳过手机号
            return not RegexMaskEngine._luhn_valid(m)  # 跳过非 Luhn 卡号

        ordered = [
            k
            for k in self.BUILTIN_RULE_ORDER
            if k in self._builtin_rules and k in self._enabled_entities
        ]
        ordered += [
            k
            for k in sorted(self._builtin_rules.keys())
            if k not in ordered and k in self._enabled_entities
        ]
        for rule_key in ordered:
            filter_fn = _bankcard_filter if rule_key == "bankcard" else None
            result = self._apply_rule(result, rule_key, mappings, stats, filter_fn)

        return result, mappings, stats

    def unmask(self, text: str, mappings: Dict[str, str]) -> str:
        """还原处理"""
        result = text
        for placeholder, real_value in mappings.items():
            result = result.replace(placeholder, real_value)
        return result

    def add_custom_keyword(self, keyword: str) -> bool:
        """添加自定义敏感词（增量构建自动机）"""
        if keyword and keyword not in self.custom_keywords:
            self.custom_keywords.append(keyword)
            self._automaton.add_word(keyword)
            return True
        return False

    def remove_custom_keyword(self, keyword: str) -> bool:
        """删除自定义敏感词（重建自动机）"""
        if keyword in self.custom_keywords:
            self.custom_keywords.remove(keyword)
            self._rebuild_automaton()
            return True
        return False

    def _rebuild_automaton(self) -> None:
        """重置并重建自动机"""
        self._automaton = AhoCorasickAutomaton()
        for kw in self.custom_keywords:
            self._automaton.add_word(kw)

    def get_custom_keywords(self) -> List[str]:
        """获取自定义敏感词列表"""
        return self.custom_keywords.copy()

    # ==================== Custom Regex Rules ====================

    def add_custom_regex_rule(self, name: str, pattern: str, entity_type: str) -> bool:
        """添加自定义正则规则（编译并存储模式）"""
        if name in self._custom_regex_rules:
            return False
        if entity_type not in KNOWN_ENTITY_TYPES:
            raise ValueError(f"未知实体类型: {entity_type}")
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"无效的正则表达式: {e}")
        self._custom_regex_rules[name] = (compiled, entity_type)
        self._disabled_custom_regex_rules.discard(name)
        logger.info(f"添加自定义正则规则: name={name}, entity_type={entity_type}")
        return True

    def remove_custom_regex_rule(self, name: str) -> bool:
        """删除自定义正则规则"""
        if name in self._custom_regex_rules:
            del self._custom_regex_rules[name]
            self._disabled_custom_regex_rules.discard(name)
            logger.info(f"删除自定义正则规则: name={name}")
            return True
        return False

    def get_custom_regex_rules(self) -> List[Dict[str, Any]]:
        """获取自定义正则规则列表（含启用状态）"""
        rules = []
        for name, (compiled, entity_type) in self._custom_regex_rules.items():
            rules.append(
                {
                    "name": name,
                    "pattern": compiled.pattern,
                    "entity_type": entity_type,
                    "enabled": name not in self._disabled_custom_regex_rules,
                }
            )
        return rules

    def toggle_custom_regex_rule(self, name: str, enabled: bool) -> bool:
        """启用/禁用自定义正则规则"""
        if name not in self._custom_regex_rules:
            return False
        if enabled:
            self._disabled_custom_regex_rules.discard(name)
        else:
            self._disabled_custom_regex_rules.add(name)
        logger.info(f"{'启用' if enabled else '禁用'}自定义正则规则: name={name}")
        return True

    def get_entity_catalog(self) -> List[Dict[str, Any]]:
        """返回实体目录元数据（供 /api/entities 等使用）。"""
        result = []
        for key, meta in self._entity_meta.items():
            result.append(
                {
                    "type": meta.get("placeholder_token") or f"PII_{key.upper()}",
                    "key": key,
                    "name": meta.get("name_zh") or meta.get("name_en", key),
                    "name_en": meta.get("name_en", key),
                    "description": meta.get("name_en", ""),
                    "enabled": key in self._enabled_entities,
                    "engine": meta.get("detector", "regex"),
                    "compliance_tag": meta.get("compliance_tag", "personal_info"),
                }
            )
        return result


def placeholder_to_token(placeholder: str) -> str:
    """从占位符解析实体 token（如 [PII_BANKCARD_A] → PII_BANK）。"""
    m = re.match(r"\[PII_(\w+)_([A-Z]+)\]", placeholder)
    if not m:
        return "unknown"
    key_upper = m.group(1)
    catalog = ENTITY_CATALOG
    if catalog:
        for key, meta in catalog.items():
            if key.upper() == key_upper:
                return meta.get("placeholder_token") or f"PII_{key.upper()}"
    return "unknown"


def compliance_tag_for_key(key: str) -> str:
    """返回实体 key 的合规分级（personal_info/important_data/core_data）。"""
    catalog = ENTITY_CATALOG
    if catalog and key in catalog:
        return catalog[key].get("compliance_tag", "personal_info")
    return "personal_info"


_COMPLIANCE_PRIORITY = {"personal_info": 1, "important_data": 2, "core_data": 3}


def dominant_compliance_tag(stats: Dict[str, int]) -> str:
    """从统计 dict 推导最高敏感度的数据分级。"""
    best = "personal_info"
    best_p = 1
    for key, count in stats.items():
        if key == "total" or count <= 0:
            continue
        tag = compliance_tag_for_key(key)
        p = _COMPLIANCE_PRIORITY.get(tag, 1)
        if p > best_p:
            best, best_p = tag, p
    return best


def create_mask_engine() -> MaskEngineInterface:
    """创建脱敏引擎"""
    logger.info("使用正则脱敏引擎 (Lite)")
    engine = RegexMaskEngine()
    try:
        from database import db

        keywords = db.get_custom_keywords()
        for kw in keywords:
            engine.add_custom_keyword(kw)
        if keywords:
            logger.info(f"从数据库加载了 {len(keywords)} 个自定义关键词")

        # 加载自定义正则规则
        rules = db.get_custom_regex_rules()
        for rule in rules:
            try:
                engine.add_custom_regex_rule(
                    rule["name"], rule["pattern"], rule["entity_type"]
                )
                if not rule["enabled"]:
                    engine.toggle_custom_regex_rule(rule["name"], False)
            except (ValueError, re.error) as e:
                logger.warning(
                    f"跳过无效的自定义正则规则 '{rule.get('name', '?')}': {e}"
                )
        if rules:
            logger.info(f"从数据库加载了 {len(rules)} 个自定义正则规则")
    except Exception as e:
        logger.warning(f"加载自定义关键词/正则规则失败: {e}")
    return engine


mask_engine: Optional[MaskEngineInterface] = None


def get_mask_engine() -> MaskEngineInterface:
    """获取脱敏引擎实例"""
    global mask_engine
    if mask_engine is None:
        mask_engine = create_mask_engine()
    return mask_engine
