"""
AC Engine 测试 - Aho-Corasick 自动机引擎
"""
import pytest
from unittest.mock import Mock, patch


class TestACEngine:
    """AC 自动机引擎测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        try:
            from ac_engine import ACEngine, get_ac_engine

            engine = get_ac_engine()
            assert engine is not None
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_add_keyword(self):
        """测试添加关键词"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("敏感词", "CUSTOM")

            # 验证关键词已添加
            text = "这是一个敏感词测试"
            matches = engine.search(text)

            assert len(matches) > 0
            assert any(m["keyword"] == "敏感词" for m in matches)
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_remove_keyword(self):
        """测试删除关键词"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("测试词", "CUSTOM")

            # 先验证存在
            text = "这是测试词"
            matches_before = engine.search(text)
            assert len(matches_before) > 0

            # 删除
            engine.remove_keyword("测试词")

            # 验证已删除
            matches_after = engine.search(text)
            assert not any(m["keyword"] == "测试词" for m in matches_after)
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_search_multiple_keywords(self):
        """测试多关键词搜索"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("关键词A", "CUSTOM")
            engine.add_keyword("关键词B", "CUSTOM")

            text = "这里包含关键词A和关键词B"
            matches = engine.search(text)

            assert len(matches) >= 2
            keywords = [m["keyword"] for m in matches]
            assert "关键词A" in keywords
            assert "关键词B" in keywords
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_search_with_positions(self):
        """测试带位置信息的搜索"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("测试", "CUSTOM")

            text = "这是一个测试文本"
            matches = engine.search(text)

            assert len(matches) > 0
            match = matches[0]
            assert "start" in match
            assert "end" in match
            assert match["start"] >= 0
            assert match["end"] > match["start"]
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_case_sensitivity(self):
        """测试大小写敏感"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("Test", "CUSTOM")

            # 测试大小写匹配
            text_lower = "这是 test 文本"
            text_upper = "这是 TEST 文本"
            text_mixed = "这是 Test 文本"

            matches_lower = engine.search(text_lower)
            matches_upper = engine.search(text_upper)
            matches_mixed = engine.search(text_mixed)

            # 根据引擎配置，验证匹配行为
            # 默认应该是大小写不敏感（中文场景）
            total_matches = len(matches_lower) + len(matches_upper) + len(matches_mixed)
            assert total_matches >= 1
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_empty_text_search(self):
        """测试空文本搜索"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("测试", "CUSTOM")

            matches = engine.search("")
            assert len(matches) == 0

            matches = engine.search(None)
            assert len(matches) == 0
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_fallback_regex(self):
        """测试回退正则匹配"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()

            # 如果AC引擎不可用，应该有回退正则
            text = "手机号13812345678"
            matches = engine.search(text)

            # 应该能匹配到手机号（通过回退正则）
            assert len(matches) > 0
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_batch_keywords(self):
        """测试批量添加关键词"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            keywords = ["词A", "词B", "词C", "词D"]
            engine.add_keywords(keywords, "CUSTOM")

            text = "包含词A、词B和词C"
            matches = engine.search(text)

            matched_keywords = [m["keyword"] for m in matches]
            assert "词A" in matched_keywords
            assert "词B" in matched_keywords
            assert "词C" in matched_keywords
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_clear_keywords(self):
        """测试清空关键词"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("临时词", "CUSTOM")

            # 清空
            engine.clear_keywords()

            # 验证已清空
            text = "这是临时词"
            matches = engine.search(text)
            assert not any(m["keyword"] == "临时词" for m in matches)
        except ImportError:
            pytest.skip("ac_engine module not available")


class TestACEnginePerformance:
    """AC 引擎性能测试"""

    def test_large_text_search(self):
        """测试大文本搜索"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()
            engine.add_keyword("目标词", "CUSTOM")

            # 生成大文本
            large_text = "普通文本 " * 1000 + "目标词" + " 普通文本" * 1000

            matches = engine.search(large_text)
            assert len(matches) >= 1
        except ImportError:
            pytest.skip("ac_engine module not available")

    def test_many_keywords_search(self):
        """测试多关键词搜索性能"""
        try:
            from ac_engine import get_ac_engine

            engine = get_ac_engine()

            # 添加100个关键词
            for i in range(100):
                engine.add_keyword(f"关键词{i}", "CUSTOM")

            text = "包含关键词50和关键词99"
            matches = engine.search(text)

            matched_keywords = [m["keyword"] for m in matches]
            assert "关键词50" in matched_keywords
            assert "关键词99" in matched_keywords
        except ImportError:
            pytest.skip("ac_engine module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])