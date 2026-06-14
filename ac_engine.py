"""
AC 自动机脱敏引擎 - 使用 Rust Aho-Corasick 实现高性能多模式匹配

企业版特性：支持数千个自定义敏感词的 O(n) 时间匹配，相比正则引擎的
O(n*m) 有显著性能提升。当 Rust 模块未构建时，自动回退到正则引擎。
"""
import re
import threading
import logging
from typing import Tuple, Dict, List, Optional

from mask_engine import MaskEngineInterface, RegexMaskEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rust 模块导入（带回退）
# ---------------------------------------------------------------------------

HAS_RUST_AC = False
try:
    from ac_matcher import build_ac, AcMatcher, AcMatch  # type: ignore
    HAS_RUST_AC = True
    logger.info("Rust AC 自动机模块加载成功")
except ImportError:
    logger.warning("Rust AC 自动机模块未构建（ac_matcher），使用纯 Python 正则回退")

# ---------------------------------------------------------------------------
# 模拟 AcMatch（回退时使用）
# ---------------------------------------------------------------------------

if not HAS_RUST_AC:

    class AcMatch:  # type: ignore
        """模拟的 AcMatch，回退时用于统一内部接口"""

        def __init__(self, pattern: str, start: int, end: int, original: str):
            self.pattern = pattern
            self.start = start
            self.end = end
            self.original = original

    class AcMatcher:  # type: ignore
        """模拟的 AcMatcher，回退时用 Python 字符串查找 + LeftmostLongest 实现"""

        def __init__(self, patterns: List[str]):
            if not patterns:
                raise ValueError("at least one pattern is required")
            self.patterns = patterns

        def find_all(self, text: str) -> List[AcMatch]:
            """实现 LeftmostLongest 语义的非重叠匹配

            算法：
            1. 找到所有模式的所有出现位置
            2. 按 (起始位置, -结束位置) 排序（左优先、长优先）
            3. 从左到右扫描，取每个位置的最长匹配
            4. 跳过已覆盖区域的起始位置
            """
            if not text:
                return []

            # Step 1: 收集所有出现
            raw: List[AcMatch] = []
            for kw in self.patterns:
                kw_len = len(kw)
                idx = 0
                while True:
                    pos = text.find(kw, idx)
                    if pos == -1:
                        break
                    raw.append(AcMatch(kw, pos, pos + kw_len, kw))
                    idx = pos + 1

            if not raw:
                return []

            # Step 2: 按起始位置升序、长度降序排序
            raw.sort(key=lambda m: (m.start, -m.end))

            # Step 3: LeftmostLongest 筛选
            results: List[AcMatch] = []
            cursor = 0

            for m in raw:
                if m.start < cursor:
                    continue  # 起始在已覆盖区域内，跳过
                # m.start >= cursor: 接受
                results.append(m)
                cursor = m.end

            return results

        def replace_all(
            self, text: str, replacements: Dict[str, str]
        ) -> str:
            matches = self.find_all(text)
            if not matches:
                return text
            result = []
            last_end = 0
            for m in matches:
                if last_end < m.start:
                    result.append(text[last_end : m.start])
                replacement = replacements.get(m.pattern, text[m.start : m.end])
                result.append(replacement)
                last_end = m.end
            if last_end < len(text):
                result.append(text[last_end:])
            return "".join(result)

        def __len__(self) -> int:
            return len(self.patterns)

    def build_ac(patterns: List[str]) -> AcMatcher:  # type: ignore
        return AcMatcher(patterns)


# ---------------------------------------------------------------------------
# AcEngine
# ---------------------------------------------------------------------------


class AcEngine(MaskEngineInterface):
    """基于 AC 自动机的脱敏引擎（企业版）

    工作流程：
    1. 使用 AC 自动机匹配自定义关键词（O(n)，单次扫描）
    2. 将结果传给正则引擎处理内置规则（手机号、邮箱等）
    3. 合并映射和统计

    当 Rust 模块未构建时，使用纯 Python 字符串查找作为回退。
    """

    _sequence_counter = 0
    _sequence_lock = threading.Lock()

    ENTITY_TYPE_MAP = {
        **RegexMaskEngine.ENTITY_TYPE_MAP,
    }

    @classmethod
    def _get_next_sequence(cls) -> str:
        with cls._sequence_lock:
            cls._sequence_counter += 1
            return f"{cls._sequence_counter:08d}"

    @staticmethod
    def _create_placeholder(entity_type: str, _value: str) -> str:
        sequence = AcEngine._get_next_sequence()
        return f"[PII_{entity_type.upper()}_{sequence}]"

    def __init__(self) -> None:
        # 内部使用正则引擎处理内置规则（手机、邮箱、身份证等）
        self._regex_engine = RegexMaskEngine()
        self._custom_keywords: List[str] = []
        self._ac: Optional[AcMatcher] = None

    # -- 自动机构建 ---------------------------------------------------------

    def _rebuild_automaton(self) -> None:
        """用当前自定义关键词重建 AC 自动机。"""
        if not self._custom_keywords:
            self._ac = None
            return
        try:
            self._ac = build_ac(self._custom_keywords)
        except Exception as e:
            logger.warning("构建 AC 自动机失败，使用回退模式: %s", e)
            self._ac = None

    # -- 脱敏核心逻辑 -------------------------------------------------------

    def _mask_custom_keywords(
        self, text: str
    ) -> Tuple[str, Dict[str, str], int]:
        """使用 AC 自动机（或回退）查找并替换自定义关键词。

        从右向左处理以确保替换位置不因前置替换而偏移。

        Returns:
            (masked_text, mappings, matched_count)
        """
        if not self._custom_keywords:
            return text, {}, 0

        ac = self._ac  # 可能为 None（回退）
        matches: List[AcMatch] = []

        if ac is not None:
            try:
                matches = ac.find_all(text)
            except Exception as e:
                logger.error("AC 查找失败: %s", e)
                ac = None

        if ac is None:
            # 回退：逐关键词扫描，排序去重
            seen: set = set()
            for kw in self._custom_keywords:
                idx = 0
                while True:
                    pos = text.find(kw, idx)
                    if pos == -1:
                        break
                    if pos not in seen:
                        seen.add(pos)
                        matches.append(AcMatch(kw, pos, pos + len(kw), kw))
                    idx = pos + 1
            matches.sort(key=lambda m: m.start)

        if not matches:
            return text, {}, 0

        # 从右向左替换，保证位置不偏移
        result = text
        mappings: Dict[str, str] = {}
        count = 0

        for m in sorted(matches, key=lambda x: x.start, reverse=True):
            if result[m.start : m.end] != m.original:
                # 该位置已被前置替换覆盖，跳过
                continue
            placeholder = self._create_placeholder("custom", m.original)
            result = result[: m.start] + placeholder + result[m.end :]
            mappings[placeholder] = m.original
            count += 1

        return result, mappings, count

    def mask(
        self, text: str
    ) -> Tuple[str, Dict[str, str], Dict[str, int]]:
        """脱敏处理

        1. 先用正则引擎处理内置规则（手机、邮箱、身份证等）
        2. 再用 AC 自动机处理自定义关键词

        先正则后 AC 的顺序确保 NER 引擎不会看到 AC 生成的占位符
        （如 [PII_CUSTOM_00000001]），避免 NER 的正则误匹配其内部数字。

        Returns:
            (masked_text, mappings, stats)
        """
        # Step 1: 内置规则（正则引擎），跳过其自定义关键词以免重复
        saved = list(self._regex_engine.custom_keywords)
        self._regex_engine.custom_keywords.clear()
        try:
            reg_result, reg_mappings, reg_stats = self._regex_engine.mask(text)
        finally:
            self._regex_engine.custom_keywords = saved

        # Step 2: 自定义关键词（AC 自动机），处理已脱敏文本
        # 正则引擎的占位符 [PII_xxx_N] 包含字母和下划线，
        # 不会匹配普通自定义关键词，因此安全。
        ac_result, ac_mappings, ac_count = self._mask_custom_keywords(reg_result)

        # Step 3: 合并
        total_stats = dict(reg_stats)
        total_stats["custom"] = ac_count

        total_mappings = dict(ac_mappings)
        total_mappings.update(reg_mappings)

        return ac_result, total_mappings, total_stats

    # -- 还原 ---------------------------------------------------------------

    def unmask(self, text: str, mappings: Dict[str, str]) -> str:
        """还原处理"""
        result = text
        for placeholder, real_value in mappings.items():
            result = result.replace(placeholder, real_value)
        return result

    # -- 自定义关键词管理 ---------------------------------------------------

    def add_custom_keyword(self, keyword: str) -> bool:
        """添加自定义敏感词并重建自动机。"""
        if not keyword:
            return False
        if keyword in self._custom_keywords:
            return False
        self._custom_keywords.append(keyword)
        self._rebuild_automaton()
        return True

    def remove_custom_keyword(self, keyword: str) -> bool:
        """删除自定义敏感词并重建自动机。"""
        if keyword not in self._custom_keywords:
            return False
        self._custom_keywords.remove(keyword)
        self._rebuild_automaton()
        return True

    def get_custom_keywords(self) -> List[str]:
        """获取自定义敏感词列表。"""
        return list(self._custom_keywords)
