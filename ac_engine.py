"""
AC 自动机脱敏引擎 - Enterprise 版
使用 pyahocorasick 实现 O(n) 匹配，支持万级词库
"""
import hashlib
import logging
from typing import Tuple, Dict, List, Set

logger = logging.getLogger(__name__)

# 尝试导入 AC 自动机库
try:
    import ahocorasick
    HAS_AHOCORASICK = True
except ImportError:
    HAS_AHOCORASICK = False
    logger.warning("pyahocorasick 未安装，回退到正则引擎")


class ACAutomatonEngine:
    """AC 自动机脱敏引擎"""

    SECRET_KEY = "ai_privacy_vault_key_2024_enterprise"

    def __init__(self):
        self.automaton = None
        self.keywords: Set[str] = set()
        self.pattern_patterns: Dict[str, str] = {}
        self._init_builtin_patterns()

    def _init_builtin_patterns(self):
        """初始化内置正则模式（用于手机号等动态模式）"""
        import re
        self.pattern_patterns = {
            "phone": re.compile(r'\b(1[3-9]\d{9})\b'),
            "email": re.compile(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'),
            "idcard": re.compile(r'\b([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])\b'),
            "bankcard": re.compile(r'\b([1-9]\d{15,18})\b'),
        }

    def _encrypt(self, text: str) -> str:
        """生成占位符哈希（确定性，相同输入产生相同占位符）"""
        return hashlib.sha256(f"{self.SECRET_KEY}_{text}".encode()).hexdigest()[:16]

    def build_automaton(self, keywords: List[str]):
        """构建 AC 自动机"""
        if not HAS_AHOCORASICK:
            logger.warning("无法构建 AC 自动机，库未安装")
            return

        self.automaton = ahocorasick.Automaton()

        for keyword in keywords:
            self.automaton.add_word(keyword, keyword)
            self.keywords.add(keyword)

        self.automaton.make_automaton()
        logger.info(f"[AC自动机] 构建完成，词库数量: {len(self.keywords)}")

    def add_keyword(self, keyword: str) -> bool:
        """添加关键词"""
        if keyword and keyword not in self.keywords:
            self.keywords.add(keyword)
            if self.automaton:
                self.automaton.add_word(keyword, keyword)
                self.automaton.make_automaton()
            return True
        return False

    def remove_keyword(self, keyword: str) -> bool:
        """删除关键词"""
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            # AC 自动机不支持动态删除，需要重建
            self.build_automaton(list(self.keywords))
            return True
        return False

    def get_keywords(self) -> List[str]:
        """获取关键词列表"""
        return list(self.keywords)

    def mask(self, text: str) -> Tuple[str, Dict[str, str], Dict[str, int]]:
        """
        AC 自动机脱敏
        返回: (脱敏后文本, 映射字典, 统计信息)
        """
        result = text
        mappings = {}
        stats = {"phone": 0, "email": 0, "idcard": 0, "bankcard": 0, "custom": 0}

        # 1. 先用正则处理动态模式（手机号等）
        for pattern_name, pattern in self.pattern_patterns.items():
            for match in pattern.findall(result):
                placeholder = f"[VAULT_{pattern_name.upper()}_{self._encrypt(match)}]"
                result = result.replace(match, placeholder)
                mappings[placeholder] = match
                stats[pattern_name] += 1

        # 2. 用 AC 自动机处理固定关键词
        if self.automaton and HAS_AHOCORASICK:
            # AC 自动机匹配
            matches = []
            for end_idx, keyword in self.automaton.iter(result):
                start_idx = end_idx - len(keyword) + 1
                matches.append((start_idx, end_idx, keyword))

            # 从右往左处理，避免替换后前序索引失效
            matches.sort(key=lambda x: x[0], reverse=True)

            for start_idx, end_idx, keyword in matches:
                placeholder = f"[VAULT_CUST_{self._encrypt(keyword)}]"
                result = result[:start_idx] + placeholder + result[end_idx + 1:]
                mappings[placeholder] = keyword
                stats["custom"] += 1

        return result, mappings, stats

    def unmask(self, text: str, mappings: Dict[str, str]) -> str:
        """还原处理"""
        result = text
        for placeholder, real_value in mappings.items():
            result = result.replace(placeholder, real_value)
        return result


class HybridMaskEngine:
    """
    混合脱敏引擎 - Enterprise 版
    正则处理动态模式 + AC 自动机处理固定词库
    """

    def __init__(self):
        self.ac_engine = ACAutomatonEngine()
        self._load_keywords()

    def _load_keywords(self):
        """加载关键词库"""
        # 从存储加载
        try:
            from redis_storage import get_storage
            storage = get_storage()
            keywords = storage.get_custom_keywords()
            if keywords:
                self.ac_engine.build_automaton(keywords)
        except:
            pass

    def add_custom_keyword(self, keyword: str) -> bool:
        """添加自定义关键词"""
        return self.ac_engine.add_keyword(keyword)

    def remove_custom_keyword(self, keyword: str) -> bool:
        """删除自定义关键词"""
        return self.ac_engine.remove_keyword(keyword)

    def get_custom_keywords(self) -> List[str]:
        """获取关键词列表"""
        return self.ac_engine.get_keywords()

    def mask(self, text: str) -> Tuple[str, Dict[str, str], Dict[str, int]]:
        """脱敏处理"""
        return self.ac_engine.mask(text)

    def unmask(self, text: str, mappings: Dict[str, str]) -> str:
        """还原处理"""
        return self.ac_engine.unmask(text, mappings)


# 全局混合引擎实例
hybrid_engine = None


def get_hybrid_engine() -> HybridMaskEngine:
    """获取混合引擎实例"""
    global hybrid_engine
    if hybrid_engine is None:
        hybrid_engine = HybridMaskEngine()
    return hybrid_engine