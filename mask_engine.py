"""
脱敏引擎模块 - 抽象接口设计
支持正则引擎 (Lite/Pro) 和 AC 自动机 (Enterprise)
"""
import re
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Tuple, Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


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
    """正则表达式脱敏引擎 - Lite/Pro 版"""

    # 加密密钥
    SECRET_KEY = "ai_privacy_vault_key_2024"

    # 内置正则规则
    BUILTIN_RULES = {
        "phone": re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)'),
        "email": re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'),
        "idcard": re.compile(r'(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)'),
        "bankcard": re.compile(r'(?<!\d)([1-9]\d{15,18})(?!\d)'),
    }

    def __init__(self):
        self.custom_keywords: List[str] = []

    def _encrypt(self, text: str) -> str:
        """生成占位符哈希（确定性）"""
        return hashlib.sha256(f"{self.SECRET_KEY}_{text}".encode()).hexdigest()[:16]

    def mask(self, text: str) -> Tuple[str, Dict[str, str], Dict[str, int]]:
        """正则脱敏处理"""
        result = text
        mappings = {}
        stats = {"phone": 0, "email": 0, "idcard": 0, "bankcard": 0, "custom": 0}

        # 1. 手机号
        for match in self.BUILTIN_RULES["phone"].findall(result):
            placeholder = f"[VAULT_PHONE_{self._encrypt(match)}]"
            result = result.replace(match, placeholder)
            mappings[placeholder] = match
            stats["phone"] += 1
            logger.debug(f"[脱敏] 手机号 -> {placeholder}")

        # 2. 邮箱
        for match in self.BUILTIN_RULES["email"].findall(result):
            placeholder = f"[VAULT_EMAIL_{self._encrypt(match)}]"
            result = result.replace(match, placeholder)
            mappings[placeholder] = match
            stats["email"] += 1
            logger.debug(f"[脱敏] 邉箱 -> {placeholder}")

        # 3. 身份证
        for match in self.BUILTIN_RULES["idcard"].findall(result):
            placeholder = f"[VAULT_IDCARD_{self._encrypt(match)}]"
            result = result.replace(match, placeholder)
            mappings[placeholder] = match
            stats["idcard"] += 1
            logger.debug(f"[脱敏] 身份证 -> {placeholder}")

        # 4. 银行卡
        for match in self.BUILTIN_RULES["bankcard"].findall(result):
            # 排除手机号格式
            if len(match) == 11 and match.startswith('1'):
                continue
            placeholder = f"[VAULT_BANK_{self._encrypt(match)}]"
            result = result.replace(match, placeholder)
            mappings[placeholder] = match
            stats["bankcard"] += 1
            logger.debug(f"[脱敏] 银行卡 -> {placeholder}")

        # 5. 自定义关键词
        for keyword in self.custom_keywords:
            if keyword in result:
                placeholder = f"[VAULT_CUST_{self._encrypt(keyword)}]"
                result = result.replace(keyword, placeholder)
                mappings[placeholder] = keyword
                stats["custom"] += 1
                logger.debug(f"[脱敏] 自定义词 '{keyword}' -> {placeholder}")

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


class ACAutomatonMaskEngine(MaskEngineInterface):
    """AC 自动机脱敏引擎 - Enterprise 版"""

    def __init__(self):
        # Enterprise 版使用 pyahocorasick
        # 这里预留接口，实际实现需要安装 pyahocorasick
        self._automaton = None
        self.custom_keywords: List[str] = []
        self._builtin_patterns: Dict[str, str] = {}
        self._init_builtin_patterns()

    def _init_builtin_patterns(self):
        """初始化内置模式"""
        # 手机号、邮箱等正则模式转换为固定模式库
        # 实际 Enterprise 版会使用更复杂的模式匹配
        pass

    def _build_automaton(self):
        """构建 AC 自动机"""
        try:
            import ahocorasick
            self._automaton = ahocorasick.Automaton()
            for keyword in self.custom_keywords:
                self._automaton.add_word(keyword, keyword)
            self._automaton.make_automaton()
        except ImportError:
            logger.warning("pyahocorasick 未安装，回退到正则引擎")

    def mask(self, text: str) -> Tuple[str, Dict[str, str], Dict[str, int]]:
        """AC 自动机脱敏"""
        if self._automaton is None:
            # 回退到正则引擎
            engine = RegexMaskEngine()
            engine.custom_keywords = self.custom_keywords
            return engine.mask(text)

        result = text
        mappings = {}
        stats = {"phone": 0, "email": 0, "idcard": 0, "bankcard": 0, "custom": 0}

        # 使用 AC 自动机匹配
        for end_idx, keyword in self._automaton.iter(text):
            start_idx = end_idx - len(keyword) + 1
            placeholder = f"[VAULT_CUST_{hashlib.sha256(keyword.encode()).hexdigest()[:16]}]"
            result = result.replace(keyword, placeholder)
            mappings[placeholder] = keyword
            stats["custom"] += 1

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
            self._build_automaton()
            return True
        return False

    def remove_custom_keyword(self, keyword: str) -> bool:
        """删除自定义敏感词"""
        if keyword in self.custom_keywords:
            self.custom_keywords.remove(keyword)
            self._build_automaton()
            return True
        return False

    def get_custom_keywords(self) -> List[str]:
        """获取自定义敏感词列表"""
        return self.custom_keywords.copy()


def create_mask_engine() -> MaskEngineInterface:
    """根据版本创建脱敏引擎"""
    if config.feature_ac_automaton:
        logger.info("使用 AC 自动机 + 正则混合脱敏引擎 (Enterprise)")
        from ac_engine import HybridMaskEngine
        engine = HybridMaskEngine()
    else:
        logger.info("使用正则脱敏引擎 (Lite/Pro)")
        engine = RegexMaskEngine()
        # 从数据库加载自定义关键词
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


# 全局引擎实例
mask_engine: Optional[MaskEngineInterface] = None


def get_mask_engine() -> MaskEngineInterface:
    """获取脱敏引擎实例"""
    global mask_engine
    if mask_engine is None:
        mask_engine = create_mask_engine()
    return mask_engine