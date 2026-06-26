"""
脱敏引擎模块 - 正则表达式脱敏引擎
支持 NER 命名实体识别，覆盖 13 种实体类型
"""
import re
import hashlib
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


KNOWN_ENTITY_TYPES = frozenset({
    "phone", "email", "idcard", "bankcard", "plate", "coordinates",
    "ip", "url", "date", "amount", "postcode",
    "passport", "ssn", "credit_code", "mac",
    "person", "location", "organization", "custom",
})


class AhoCorasickAutomaton:
    """Aho-Corasick 多模式匹配自动机

    支持多关键词同时搜索，一次遍历文本即可找出所有匹配。
    返回结果按匹配长度降序排列（最长匹配优先）。
    仅使用 Python 标准库实现，无需外部依赖。
    """

    class _Node:
        """Trie 节点"""
        __slots__ = ('children', 'fail', 'output')

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


class RegexMaskEngine(MaskEngineInterface):
    """正则表达式脱敏引擎"""

    # 占位符使用随机序列号标识，无需固定密钥
    _sequence_counter = 0
    _sequence_lock = threading.Lock()

    BUILTIN_RULES = {
        "phone": re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)'),
        "email": re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'),
        "idcard": re.compile(r'(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)'),
        "bankcard": re.compile(r'(?<!\d)([1-9]\d{15,18})(?!\d)'),
        "plate": re.compile(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}'),
        "coordinates": re.compile(r'(?<!\d)(\d{1,3}\.\d{4,}\s*[,，\s]\s*\d{1,3}\.\d{4,})(?!\d)'),
        "ip": re.compile(r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'),
        "url": re.compile(r'https?://[^\s]+'),
        "date": re.compile(r'\d{4}[-/年](?:0?[1-9]|1[0-2])[-/月](?:0?[1-9]|[12]\d|3[01])日?'),
        "amount": re.compile(r'(?:¥|￥|\$)\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?'),
        # 邮编 - 注意：可能误匹配6位连续数字（如订单号、快递单号等）
        "postcode": re.compile(r'(?<!\d)([1-9]\d{5})(?!\d)'),
        "passport": re.compile(r'(?<![A-Z])(E\d{8})(?!\d)'),
        "ssn": re.compile(r'(?<!\d)(\d{3}-\d{2}-\d{4})(?!\d)'),
        "credit_code": re.compile(r'(?<![A-Z0-9])([0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10})(?![A-Z0-9])'),
        "mac": re.compile(r'(?i)(?<![0-9A-F])([0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2}[:-][0-9A-F]{2})(?![0-9A-F])'),
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
    }

    def __init__(self):
        self.custom_keywords: List[str] = []
        self._automaton = AhoCorasickAutomaton()
        self._custom_regex_rules: Dict[str, Tuple[re.Pattern, str]] = {}
        self._disabled_custom_regex_rules: set = set()
        self._ner_engine = None
        if HAS_NER:
            self._ner_engine = get_ner_engine()

    @staticmethod
    def _to_alpha_id(n: int) -> str:
        """将正整数转为纯字母 ID（A, B, ..., Z, AA, AB, ...）。

        避免占位符中出现数字，防止 NER/内置规则误匹配占位符内的数字序列。
        """
        result = []
        while n > 0:
            n -= 1
            result.append(chr(ord('A') + (n % 26)))
            n //= 26
        return ''.join(reversed(result))

    @classmethod
    def _get_next_sequence(cls) -> str:
        with cls._sequence_lock:
            cls._sequence_counter += 1
            return cls._to_alpha_id(cls._sequence_counter)

    def _create_placeholder(self, entity_type: str, value: str) -> str:
        sequence = self._get_next_sequence()
        return f"[PII_{entity_type.upper()}_{sequence}]"

    def _apply_rule(self, result: str, rule_key: str,
                    mappings: Dict[str, str], stats: Dict[str, int],
                    filter_fn=None) -> str:
        """Apply a single built-in regex rule to the text.

        Uses position-based replacement to avoid over-replacing when
        the same PII value appears multiple times in the text.
        The optional filter_fn(match) should return True to skip the match.
        """
        replacements = []
        for match in self.BUILTIN_RULES[rule_key].finditer(result):
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
        stats: Dict[str, int] = {
            "phone": 0, "email": 0, "idcard": 0, "bankcard": 0,
            "plate": 0, "coordinates": 0, "ip": 0, "url": 0, "date": 0, "amount": 0, "postcode": 0,
            "passport": 0, "ssn": 0, "credit_code": 0, "mac": 0,
            "person": 0, "location": 0, "organization": 0, "custom": 0
        }

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
        for rule_name, (compiled_regex, entity_type) in self._custom_regex_rules.items():
            if rule_name in self._disabled_custom_regex_rules:
                continue
            rule_replacements = []
            for match in compiled_regex.finditer(result):
                match_str = match.group(0)
                placeholder = self._create_placeholder(entity_type, match_str)
                rule_replacements.append((match.start(), match.end(), placeholder, match_str))
                mappings[placeholder] = match_str
                if entity_type in stats:
                    stats[entity_type] += 1
            for start, end, placeholder, _ in sorted(rule_replacements, key=lambda x: -x[0]):
                result = result[:start] + placeholder + result[end:]

        # 3. NER 引擎检测人名、地名、机构名
        if self._ner_engine:
            entities = self._ner_engine.detect(result)
            for entity in entities:
                entity_type = entity.entity_type.value.lower()
                if entity_type in stats:
                    placeholder = self._create_placeholder(entity_type, entity.value)
                    result = result.replace(entity.value, placeholder)
                    mappings[placeholder] = entity.value
                    stats[entity_type] += 1

        # 4. 内置规则（银行卡需跳过11位手机号误匹配）
        _not_bankcard = lambda m: len(m) == 11 and m.startswith('1')
        for rule_key in ("phone", "email", "idcard", "bankcard", "plate",
                          "coordinates", "ip", "url", "date", "amount", "postcode",
                          "passport", "ssn", "credit_code", "mac"):
            filter_fn = _not_bankcard if rule_key == "bankcard" else None
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
            rules.append({
                "name": name,
                "pattern": compiled.pattern,
                "entity_type": entity_type,
                "enabled": name not in self._disabled_custom_regex_rules,
            })
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
                engine.add_custom_regex_rule(rule["name"], rule["pattern"], rule["entity_type"])
                if not rule["enabled"]:
                    engine.toggle_custom_regex_rule(rule["name"], False)
            except (ValueError, re.error) as e:
                logger.warning(f"跳过无效的自定义正则规则 '{rule.get('name', '?')}': {e}")
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
