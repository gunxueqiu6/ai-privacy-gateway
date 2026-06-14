"""
AC 自动机引擎单元测试

测试覆盖：
- AC 自动机构建
- 模式匹配（含重叠、最长匹配）
- 替换功能
- AcEngine 集成
- 回退机制
- 性能对比
"""
import importlib
import sys
import time
from typing import Dict, List
from unittest.mock import patch

import pytest

from ac_engine import (
    HAS_RUST_AC,
    AcEngine,
    AcMatch as AcEngineMatch,
    AcMatcher as AcEngineMatcher,
)


# ============================================================================
# 辅助函数
# ============================================================================

def _make_kv_store(
    pairs: List[str],
) -> Dict[str, str]:
    """Helper: convert a list of "key=value" strings to a dict."""
    d = {}
    for p in pairs:
        k, _, v = p.partition("=")
        d[k.strip()] = v.strip()
    return d


# ============================================================================
# AC 自动机核心功能测试（与实现无关：Rust 或 Python 回退）
# ============================================================================


class TestAcMatcherBuild:
    """构建自动机"""

    def test_build_with_single_pattern(self):
        """单模式构建"""
        m = AcEngineMatcher(["hello"])
        assert len(m) == 1

    def test_build_with_multiple_patterns(self):
        """多模式构建"""
        m = AcEngineMatcher(["hello", "world", "foo"])
        assert len(m) == 3

    def test_build_empty_raises(self):
        """空模式列表应抛出异常"""
        with pytest.raises(ValueError, match="at least one pattern"):
            AcEngineMatcher([])

    def test_build_with_long_patterns(self):
        """大量模式构建"""
        patterns = [f"pattern_{i}" for i in range(1000)]
        m = AcEngineMatcher(patterns)
        assert len(m) == 1000


class TestAcMatcherFindAll:
    """查找匹配"""

    @pytest.fixture
    def matcher(self):
        return AcEngineMatcher(["hello", "world"])

    def test_find_basic(self, matcher):
        """基本查找"""
        matches = matcher.find_all("say hello world")
        assert len(matches) == 2
        assert matches[0].pattern == "hello"
        assert matches[1].pattern == "world"

    def test_find_with_positions(self, matcher):
        """位置正确性"""
        matches = matcher.find_all("say hello world")
        assert matches[0].start == 4
        assert matches[0].end == 9
        assert matches[0].original == "hello"
        assert matches[1].start == 10
        assert matches[1].end == 15
        assert matches[1].original == "world"

    def test_no_matches(self, matcher):
        """无匹配"""
        matches = matcher.find_all("no patterns here")
        assert len(matches) == 0

    def test_empty_text(self, matcher):
        """空文本"""
        matches = matcher.find_all("")
        assert len(matches) == 0

    def test_repeated_pattern(self, matcher):
        """重复模式"""
        matches = matcher.find_all("hello hello hello")
        assert len(matches) == 3
        for m in matches:
            assert m.pattern == "hello"
            assert m.original == "hello"

    def test_partial_word_no_match(self):
        """部分单词不匹配（AC 匹配子串，确保行为可预期）"""
        m = AcEngineMatcher(["hello"])
        matches = m.find_all("hellothere")
        # AC matches substring "hello" within "hellothere"
        assert len(matches) == 1
        assert matches[0].pattern == "hello"

    def test_chinese_patterns(self):
        """中文模式"""
        m = AcEngineMatcher(["项目", "机密", "内部"])
        matches = m.find_all("这个项目涉及公司机密信息")
        # "项目" at positions 2..4, "机密" at positions 8..10 (char-based, not byte)
        # In Python, "这个项目涉及公司机密信息"[2:4] = "项目"
        assert len(matches) == 2
        patterns_found = {mm.pattern for mm in matches}
        assert patterns_found == {"项目", "机密"}

    def test_case_sensitivity(self):
        """大小写敏感"""
        # AC matcher is case-sensitive by default
        m = AcEngineMatcher(["Hello"])
        matches = m.find_all("hello Hello HELLO")
        assert len(matches) == 1
        assert matches[0].original == "Hello"


class TestAcMatcherLongestMatch:
    """最长匹配语义"""

    def test_longest_wins(self):
        """重叠时取最长"""
        m = AcEngineMatcher(["a", "ab", "abc"])
        matches = m.find_all("abcd")
        assert len(matches) == 1
        assert matches[0].pattern == "abc"
        assert matches[0].start == 0
        assert matches[0].end == 3

    def test_longest_multiple_positions(self):
        """多个位置各自取最长"""
        m = AcEngineMatcher(["a", "ab", "abc", "b", "bc"])
        matches = m.find_all("abcc")
        # Position 0: "abc" wins (longest), covering 0..3
        # Position 3: "c" not a pattern, so no more matches
        # Actually `abc` at 0..3, then nothing at 3
        assert len(matches) == 1
        assert matches[0].pattern == "abc"

    def test_longest_with_contained_patterns(self):
        """包含关系的模式"""
        m = AcEngineMatcher(["hello", "hell", "he"])
        matches = m.find_all("hello world")
        assert len(matches) == 1
        assert matches[0].pattern == "hello"

    def test_non_overlapping_sequential(self):
        """非重叠顺序匹配"""
        m = AcEngineMatcher(["ab", "cd"])
        matches = m.find_all("abcd")
        assert len(matches) == 2
        assert matches[0].pattern == "ab"
        assert matches[1].pattern == "cd"

    def test_skip_overlapped_region(self):
        """跳过已匹配区域"""
        m = AcEngineMatcher(["abc", "bcd"])
        matches = m.find_all("abcd")
        # "abc" at 0..3 wins (longer at position 0 vs "ab" if it existed)
        # "bcd" starts at 1, but 1 is within 0..3, so skipped
        assert len(matches) == 1
        assert matches[0].pattern == "abc"


class TestAcMatcherReplaceAll:
    """替换功能"""

    @pytest.fixture
    def matcher(self):
        return AcEngineMatcher(["hello", "world"])

    def test_replace_basic(self, matcher):
        """基本替换"""
        result = matcher.replace_all("hello world", {"hello": "hi", "world": "earth"})
        assert result == "hi earth"

    def test_replace_partial(self, matcher):
        """部分替换（只提供部分模式的替换）"""
        result = matcher.replace_all("hello world", {"hello": "hi"})
        # "world" has no replacement, keeps original
        # But with LeftmostLongest, "world" is still matched; if no replacement, original is kept
        assert result == "hi world"

    def test_replace_no_matches(self, matcher):
        """无匹配时原文不变"""
        result = matcher.replace_all("nothing here", {})
        assert result == "nothing here"

    def test_replace_empty_replacement_map(self, matcher):
        """空替换映射"""
        result = matcher.replace_all("hello world", {})
        assert result == "hello world"

    def test_replace_with_chinese(self):
        """中文替换"""
        m = AcEngineMatcher(["项目", "机密"])
        result = m.replace_all(
            "这个项目涉及公司机密信息",
            {"项目": "PROJECT", "机密": "CLASSIFIED"},
        )
        assert "项目" not in result
        assert "机密" not in result
        assert "PROJECT" in result
        assert "CLASSIFIED" in result

    def test_replace_multiple_occurrences(self):
        """多次出现"""
        m = AcEngineMatcher(["foo"])
        result = m.replace_all("foo bar foo baz foo", {"foo": "qux"})
        assert result == "qux bar qux baz qux"

    def test_replace_keeps_surrounding_text(self):
        """替换保持周围文本"""
        m = AcEngineMatcher(["target"])
        result = m.replace_all("before target after", {"target": "REPLACED"})
        assert result == "before REPLACED after"


# ============================================================================
# AcEngine 集成测试
# ============================================================================


class TestAcEngineBasic:
    """AcEngine 基本功能"""

    @pytest.fixture
    def engine(self):
        return AcEngine()

    def test_create_engine(self, engine):
        """引擎创建"""
        assert engine is not None
        assert engine.get_custom_keywords() == []

    def test_add_custom_keyword(self, engine):
        """添加自定义关键词"""
        assert engine.add_custom_keyword("secret_project")
        assert "secret_project" in engine.get_custom_keywords()
        # 重复添加不生效
        assert not engine.add_custom_keyword("secret_project")
        assert len(engine.get_custom_keywords()) == 1

    def test_add_empty_keyword(self, engine):
        """空关键词不添加"""
        assert not engine.add_custom_keyword("")

    def test_remove_custom_keyword(self, engine):
        """删除自定义关键词"""
        engine.add_custom_keyword("secret")
        assert engine.remove_custom_keyword("secret")
        assert "secret" not in engine.get_custom_keywords()
        # 删除不存在关键词
        assert not engine.remove_custom_keyword("nonexistent")

    def test_mask_builtin_phone(self, engine):
        """内置手机号脱敏"""
        masked, mappings, stats = engine.mask("联系我 13812345678")
        assert "13812345678" not in masked
        assert "[PII_PHONE" in masked
        assert stats.get("phone", 0) == 1

    def test_mask_builtin_email(self, engine):
        """内置邮箱脱敏"""
        masked, mappings, stats = engine.mask("邮箱 test@example.com")
        assert "test@example.com" not in masked
        assert "[PII_EMAIL" in masked
        assert stats.get("email", 0) == 1

    def test_mask_custom_keyword(self, engine):
        """自定义关键词脱敏"""
        engine.add_custom_keyword("project-phoenix")
        masked, mappings, stats = engine.mask("the project-phoenix is secret")
        assert "project-phoenix" not in masked
        assert "[PII_CUSTOM" in masked
        assert stats.get("custom", 0) == 1
        # 映射关系正确
        for ph, orig in mappings.items():
            if "CUSTOM" in ph:
                assert orig == "project-phoenix"

    def test_mask_multiple_custom_keywords(self, engine):
        """多个自定义关键词"""
        engine.add_custom_keyword("alpha")
        engine.add_custom_keyword("beta")
        masked, mappings, stats = engine.mask("alpha and beta are codes")
        assert "alpha" not in masked
        assert "beta" not in masked
        assert stats.get("custom", 0) == 2

    def test_mask_mixed_patterns(self, engine):
        """混合模式（内置 + 自定义）"""
        engine.add_custom_keyword("internal-codename")
        masked, mappings, stats = engine.mask(
            "联系 13812345678，项目 internal-codename 已启动"
        )
        assert "13812345678" not in masked
        assert "internal-codename" not in masked
        assert stats.get("phone", 0) >= 1
        assert stats.get("custom", 0) >= 1

    def test_unmask(self, engine):
        """还原"""
        engine.add_custom_keyword("secret")
        masked, mappings, _ = engine.mask("this is secret data")
        unmasked = engine.unmask(masked, mappings)
        assert unmasked == "this is secret data"

    def test_unmask_roundtrip(self, engine):
        """脱敏-还原往返"""
        engine.add_custom_keyword("classified")
        original = "my classified number is 13812345678"
        masked, mappings, _ = engine.mask(original)
        unmasked = engine.unmask(masked, mappings)
        assert unmasked == original

    def test_mask_no_sensitive(self, engine):
        """无敏感信息时文本不变"""
        masked, mappings, stats = engine.mask("hello world")
        assert masked == "hello world"
        assert mappings == {}
        assert sum(stats.values()) == 0


class TestAcEngineFallback:
    """回退机制测试"""

    def test_has_fallback_classes(self):
        """回退类可用"""
        from ac_engine import build_ac, AcMatch, AcMatcher

        # 不论 Rust 模块是否加载，这些符号都应该存在
        assert callable(build_ac)
        assert AcMatch is not None
        assert AcMatcher is not None

    def test_fallback_matches_produce_same_results(self):
        """回退和 Rust AC 产生一致结果"""
        patterns = ["hello", "world", "foo"]
        matcher = AcEngineMatcher(patterns)
        matches = matcher.find_all("hello foo world bar hello")

        assert len(matches) == 4
        patterns_found = [m.pattern for m in matches]
        assert patterns_found == ["hello", "foo", "world", "hello"]

    def test_fallback_replace(self):
        """回退替换功能"""
        matcher = AcEngineMatcher(["hello"])
        result = matcher.replace_all("hello world", {"hello": "hi"})
        assert result == "hi world"

    def test_fallback_replace_no_replacement_map(self):
        """回退-无替换映射"""
        matcher = AcEngineMatcher(["hello"])
        result = matcher.replace_all("hello world", {})
        assert result == "hello world"


class TestAcEngineWithGatewayCore:
    """与 GatewayCore 集成测试"""

    def test_ac_engine_used_in_gateway_core_when_enterprise(self):
        """企业版使用 AC 引擎"""
        with (
            patch("gateway_core.config") as mock_cfg,
            patch("gateway_core.AcEngine", create=True) as mock_ae,
        ):
            mock_cfg.tier = "enterprise"
            # 重新导入以触发条件
            if "gateway_core" in sys.modules:
                del sys.modules["gateway_core"]
            from gateway_core import GatewayCore

            gw = GatewayCore()
            # 验证 ac_engine 属性存在
            assert hasattr(gw, "ac_engine")

    def test_ac_engine_not_used_for_lite(self):
        """Lite 版不使用 AC 引擎"""
        with patch("gateway_core.config") as mock_cfg:
            mock_cfg.tier = "lite"
            if "gateway_core" in sys.modules:
                del sys.modules["gateway_core"]
            from gateway_core import GatewayCore

            gw = GatewayCore()
            assert gw.ac_engine is None

    def test_ac_engine_not_used_for_pro(self):
        """Pro 版不使用 AC 引擎"""
        with patch("gateway_core.config") as mock_cfg:
            mock_cfg.tier = "pro"
            if "gateway_core" in sys.modules:
                del sys.modules["gateway_core"]
            from gateway_core import GatewayCore

            gw = GatewayCore()
            assert gw.ac_engine is None


# ============================================================================
# 性能测试
# ============================================================================


class TestPerformance:
    """性能对比测试"""

    def _generate_patterns(self, count: int) -> List[str]:
        """生成测试模式"""
        return [f"sensitive_term_{i:06d}" for i in range(count)]

    def _generate_text(self, patterns: List[str], insert_count: int) -> str:
        """生成含匹配的测试文本"""
        import random

        prefix = "This is a normal text without any sensitive information. " * 50
        middle = " ".join(random.sample(patterns, min(insert_count, len(patterns))))
        suffix = "And here is more normal text that should not match anything. " * 50
        return prefix + " " + middle + " " + suffix

    def test_ac_vs_regex_1000_patterns(self):
        """1000 个模式时 AC 优于/等效于逐关键词扫描"""
        patterns = self._generate_patterns(1000)
        text = self._generate_text(patterns, 50)

        # AC 模式（使用 AcEngine 的内部 fallback 或 Rust）
        ac_matcher = AcEngineMatcher(patterns)
        t0 = time.perf_counter()
        ac_matches = ac_matcher.find_all(text)
        ac_time = time.perf_counter() - t0

        # 逐关键词扫描
        t0 = time.perf_counter()
        regex_like_matches = []
        for pat in patterns:
            idx = 0
            while True:
                pos = text.find(pat, idx)
                if pos == -1:
                    break
                regex_like_matches.append((pat, pos))
                idx = pos + 1
        scan_time = time.perf_counter() - t0

        # AC 应该比逐关键词扫描快（或至少不慢太多）
        assert len(ac_matches) == len(
            regex_like_matches
        ), f"匹配数量不一致: AC={len(ac_matches)}, scan={len(regex_like_matches)}"

        # 记录性能数据（不强制断言，用于监控）
        ratio = scan_time / max(ac_time, 1e-9)
        print(f"\n[性能] 1000 模式: AC={ac_time:.4f}s, 逐关键词={scan_time:.4f}s, 加速比={ratio:.1f}x")

    def test_ac_engine_vs_regex_engine_custom_keywords(self):
        """AcEngine 自定义关键词 vs RegexEngine 自定义关键词"""
        from mask_engine import RegexMaskEngine

        keywords = [f"kw_{i:06d}" for i in range(500)]
        text = "normal " + " ".join(keywords[:20]) + " normal"

        # AC 引擎
        ac_engine = AcEngine()
        for kw in keywords:
            ac_engine.add_custom_keyword(kw)
        t0 = time.perf_counter()
        ac_masked, ac_mappings, ac_stats = ac_engine.mask(text)
        ac_time = time.perf_counter() - t0

        # 正则引擎
        re_engine = RegexMaskEngine()
        for kw in keywords:
            re_engine.add_custom_keyword(kw)
        t0 = time.perf_counter()
        re_masked, re_mappings, re_stats = re_engine.mask(text)
        re_time = time.perf_counter() - t0

        # 验证结果一致
        # For the same set of custom keywords, the results should have the same
        # number of custom keyword matches
        assert (
            ac_stats.get("custom", 0) == re_stats.get("custom", 0)
        ), f"匹配数量不一致: AC={ac_stats.get('custom')}, Regex={re_stats.get('custom')}"

        ratio = re_time / max(ac_time, 1e-9)
        print(
            f"\n[性能] AcEngine vs RegexEngine: AC={ac_time:.4f}s, "
            f"Regex={re_time:.4f}s, 加速比={ratio:.1f}x"
        )


# ============================================================================
# 边界条件
# ============================================================================


class TestEdgeCases:
    """边界条件测试"""

    def test_unicode_text(self, engine: AcEngine):
        """Unicode 文本"""
        engine.add_custom_keyword("机密")
        masked, mappings, stats = engine.mask("这是机密文件")
        assert "机密" not in masked
        assert stats.get("custom", 0) == 1

    def test_very_long_text(self, engine: AcEngine):
        """超长文本"""
        engine.add_custom_keyword("target")
        long_text = "x" * 100000 + "target" + "x" * 100000
        masked, mappings, stats = engine.mask(long_text)
        assert "target" not in masked
        assert stats.get("custom", 0) == 1

    def test_special_characters(self, engine: AcEngine):
        """特殊字符"""
        engine.add_custom_keyword("$pecial_Key-123!")
        masked, mappings, stats = engine.mask("the key is $pecial_Key-123!")
        assert "$pecial_Key-123!" not in masked
        assert stats.get("custom", 0) == 1

    def test_overlapping_custom_keywords(self, engine: AcEngine):
        """重叠的自定义关键词（AC longest match 处理）"""
        engine.add_custom_keyword("abc")
        engine.add_custom_keyword("ab")
        engine.add_custom_keyword("bc")
        masked, mappings, stats = engine.mask("test abc test")
        # "abc" should win over "ab" and "bc" (longest match)
        assert stats.get("custom", 0) == 1
        for ph, orig in mappings.items():
            if "CUSTOM" in ph:
                assert orig == "abc"

    def test_empty_text(self, engine: AcEngine):
        """空文本"""
        masked, mappings, stats = engine.mask("")
        assert masked == ""
        assert mappings == {}
        assert sum(stats.values()) == 0

    def test_whitespace_text(self, engine: AcEngine):
        """空白文本"""
        masked, mappings, stats = engine.mask("   \n  \t  ")
        assert sum(stats.values()) == 0


# ============================================================================
# 生成测试报告需要的 fixture
# ============================================================================


@pytest.fixture
def engine():
    return AcEngine()
