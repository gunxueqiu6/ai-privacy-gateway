"""
脱敏引擎模块 - 正则表达式脱敏引擎
支持 NER 命名实体识别，覆盖 13 种实体类型
"""
import re
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from ner_engine import get_ner_engine, NEREntityType
    HAS_NER = True
except ImportError:
    HAS_NER = False
    logger.warning("NER engine not available, using regex only")


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


class RegexMaskEngine(MaskEngineInterface):
    """正则表达式脱敏引擎"""

    # 占位符使用随机序列号标识，无需固定密钥
    _sequence_counter = 0

    BUILTIN_RULES = {
        "phone": re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)'),
        "email": re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'),
        "idcard": re.compile(r'(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)'),
        "bankcard": re.compile(r'(?<!\d)([1-9]\d{15,18})(?!\d)'),
        "plate": re.compile(r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}'),
        "ip": re.compile(r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'),
        "url": re.compile(r'https?://[^\s]+'),
        "date": re.compile(r'\d{4}[-/年](?:0?[1-9]|1[0-2])[-/月](?:0?[1-9]|[12]\d|3[01])日?'),
        "amount": re.compile(r'(?:¥|￥|\$)\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?'),
        # 邮编 - 注意：可能误匹配6位连续数字（如订单号、快递单号等）
        "postcode": re.compile(r'(?<!\d)([1-9]\d{5})(?!\d)'),
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
    }

    def __init__(self):
        self.custom_keywords: List[str] = []
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
        import threading
        with threading.Lock():
            cls._sequence_counter += 1
            return cls._to_alpha_id(cls._sequence_counter)

    def _create_placeholder(self, entity_type: str, value: str) -> str:
        sequence = self._get_next_sequence()
        return f"[PII_{entity_type.upper()}_{sequence}]"

    def _apply_rule(self, result: str, rule_key: str,
                    mappings: Dict[str, str], stats: Dict[str, int],
                    filter_fn=None) -> str:
        """Apply a single built-in regex rule to the text.

        For each match found, creates a placeholder, updates mappings and stats.
        The optional filter_fn(match) should return True to skip the match.
        """
        for match in self.BUILTIN_RULES[rule_key].findall(result):
            if filter_fn and filter_fn(match):
                continue
            placeholder = self._create_placeholder(rule_key, match)
            result = result.replace(match, placeholder)
            mappings[placeholder] = match
            stats[rule_key] += 1
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
            "plate": 0, "ip": 0, "url": 0, "date": 0, "amount": 0, "postcode": 0,
            "person": 0, "location": 0, "organization": 0, "custom": 0
        }

        # 1. 自定义关键词优先处理
        for keyword in sorted(self.custom_keywords, key=len, reverse=True):
            if keyword in result:
                placeholder = self._create_placeholder("custom", keyword)
                result = result.replace(keyword, placeholder)
                mappings[placeholder] = keyword
                stats["custom"] += 1

        # 2. NER 引擎检测人名、地名、机构名
        if self._ner_engine:
            entities = self._ner_engine.detect(result)
            for entity in entities:
                entity_type = entity.entity_type.value.lower()
                if entity_type in stats:
                    placeholder = self._create_placeholder(entity_type, entity.value)
                    result = result.replace(entity.value, placeholder)
                    mappings[placeholder] = entity.value
                    stats[entity_type] += 1

        # 3. 内置规则（银行卡需跳过11位手机号误匹配）
        _not_bankcard = lambda m: len(m) == 11 and m.startswith('1')
        for rule_key in ("phone", "email", "idcard", "bankcard", "plate",
                          "ip", "url", "date", "amount", "postcode"):
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
        """添加自定义敏感词"""
        if keyword and keyword not in self.custom_keywords:
            self.custom_keywords.append(keyword)
            return True
        return False

    def remove_custom_keyword(self, keyword: str) -> bool:
        """删除自定义敏感词"""
        if keyword in self.custom_keywords:
            self.custom_keywords.remove(keyword)
            return True
        return False

    def get_custom_keywords(self) -> List[str]:
        """获取自定义敏感词列表"""
        return self.custom_keywords.copy()


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
    except Exception as e:
        logger.warning(f"加载自定义关键词失败: {e}")
    return engine


mask_engine: Optional[MaskEngineInterface] = None


def get_mask_engine() -> MaskEngineInterface:
    """获取脱敏引擎实例"""
    global mask_engine
    if mask_engine is None:
        mask_engine = create_mask_engine()
    return mask_engine
