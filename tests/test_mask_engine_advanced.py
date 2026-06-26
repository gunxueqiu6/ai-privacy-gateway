"""
Advanced mask engine tests — custom regex rules, edge cases, Aho-Corasick.
"""
import pytest
import re


class TestCustomRegexRules:
    """Custom regex rule management"""

    def test_add_custom_regex_rule(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        assert engine.add_custom_regex_rule("my_test_rule", r"\bSECRET_\w+\b", "custom")
        rules = engine.get_custom_regex_rules()
        names = [r["name"] for r in rules]
        assert "my_test_rule" in names
        engine.remove_custom_regex_rule("my_test_rule")

    def test_add_duplicate_rule_returns_false(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        engine.add_custom_regex_rule("dup_rule", r"\d+", "custom")
        assert engine.add_custom_regex_rule("dup_rule", r"\w+", "custom") is False
        engine.remove_custom_regex_rule("dup_rule")

    def test_add_invalid_regex_raises(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        with pytest.raises(ValueError, match="无效的正则表达式"):
            engine.add_custom_regex_rule("bad", r"[invalid", "custom")

    def test_add_unknown_entity_type_raises(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        with pytest.raises(ValueError, match="未知实体类型"):
            engine.add_custom_regex_rule("bad_type", r"\d+", "nonexistent_type")

    def test_remove_nonexistent_rule_returns_false(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        assert engine.remove_custom_regex_rule("i_dont_exist") is False

    def test_remove_rule_stops_masking(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        engine.add_custom_regex_rule("secret_tag", r"TOP_SECRET", "custom")
        masked, _, stats = engine.mask("This is TOP_SECRET data")
        assert "[PII_CUSTOM_" in masked
        engine.remove_custom_regex_rule("secret_tag")
        masked2, _, stats2 = engine.mask("This is TOP_SECRET data")
        assert "TOP_SECRET" in masked2  # no longer masked

    def test_toggle_rule_disables_it(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        engine.add_custom_regex_rule("tog_rule", r"VISIBLE", "custom")
        engine.toggle_custom_regex_rule("tog_rule", enabled=False)
        rule_info = [r for r in engine.get_custom_regex_rules() if r["name"] == "tog_rule"]
        assert len(rule_info) == 1
        assert rule_info[0]["enabled"] is False
        engine.remove_custom_regex_rule("tog_rule")

    def test_toggle_nonexistent_returns_false(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        assert engine.toggle_custom_regex_rule("no_such_rule", True) is False

    def test_custom_regex_masks_actual_text(self):
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        engine.add_custom_regex_rule("credit_card", r"\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "custom")
        masked, mappings, stats = engine.mask("My card: 4111-1111-1111-1111")
        assert "4111-1111-1111-1111" not in masked
        assert stats["custom"] >= 1
        engine.remove_custom_regex_rule("credit_card")


class TestAhoCorasickEdgeCases:
    """Aho-Corasick automaton edge cases"""

    def test_empty_text(self):
        from mask_engine import AhoCorasickAutomaton
        ac = AhoCorasickAutomaton()
        ac.add_word("test")
        matches = ac.search("")
        assert len(matches) == 0

    def test_no_keywords_added(self):
        from mask_engine import AhoCorasickAutomaton
        ac = AhoCorasickAutomaton()
        matches = ac.search("anything here")
        assert len(matches) == 0

    def test_add_empty_word(self):
        from mask_engine import AhoCorasickAutomaton
        ac = AhoCorasickAutomaton()
        ac.add_word("")  # should not raise (early return, no-op)
        assert ac._word_count == 0  # not incremented for empty word
        # After add_word(""), we should not crash on search
        matches = ac.search("test")
        assert len(matches) == 0  # empty word matches nothing

    def test_overlapping_keywords_longest_first(self):
        from mask_engine import AhoCorasickAutomaton
        ac = AhoCorasickAutomaton()
        ac.add_word("apple")
        ac.add_word("app")
        ac.add_word("application")
        matches = ac.search("I have an application")
        # Should find "application" (longest), then "apple" overlaps, etc.
        if matches:
            longest = max(matches, key=lambda m: m[1] - m[0])
            assert longest[2] == "application"

    def test_chinese_keywords(self):
        from mask_engine import AhoCorasickAutomaton
        ac = AhoCorasickAutomaton()
        ac.add_word("密码")
        ac.add_word("验证码")
        matches = ac.search("请输入密码和验证码")
        assert len(matches) >= 2
        matched_words = [m[2] for m in matches]
        assert "密码" in matched_words
        assert "验证码" in matched_words

    def test_duplicate_matches_deduped(self):
        from mask_engine import AhoCorasickAutomaton
        ac = AhoCorasickAutomaton()
        ac.add_word("test")
        matches = ac.search("test test test")
        # Should report each occurrence once
        starts = [m[0] for m in matches]
        assert len(starts) == 3  # 3 occurrences at positions 0, 5, 10


class TestMaskEngineAdvancedEdgeCases:
    """Advanced mask engine edge cases"""

    def test_empty_text(self):
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        masked, mappings, stats = engine.mask("")
        assert masked == ""
        assert mappings == {}
        assert all(v == 0 for v in stats.values())

    def test_text_with_no_pii(self):
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "这是一段完全普通的文本，没有任何敏感信息。"
        masked, mappings, stats = engine.mask(text)
        assert masked == text
        assert mappings == {}

    def test_very_long_text(self):
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        long_payload = "用户手机号是13812345678，请勿泄露。" * 500
        masked, mappings, stats = engine.mask(long_payload)
        assert "13812345678" not in masked
        assert stats["phone"] >= 500

    def test_all_pii_types_mixed(self):
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = (
            "手机13812345678 "
            "邮箱test@example.com "
            "身份证110101199001011234 "
            "银行卡6222021234567890123 "
            "车牌京A12345 "
            "IP192.168.1.1 "
            "网址https://example.com "
            "日期2024-01-15 "
            "金额¥1,234.56 "
            "邮编100081 "
            "护照E12345678 "
            "SSN123-45-6789 "
            "信用代码91310000306245892U "
            "MAC00:1A:2B:3C:4D:5E"
        )
        masked, mappings, stats = engine.mask(text)
        assert "13812345678" not in masked
        assert "test@example.com" not in masked
        assert "110101199001011234" not in masked
        assert "91310000306245892U" not in masked
        assert stats["phone"] >= 1
        assert stats["email"] >= 1
        assert stats["idcard"] >= 1
        assert stats["bankcard"] >= 1

    def test_unmask_with_partial_mappings(self):
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        text = "手机13812345678和邮箱test@example.com"
        masked, mappings, stats = engine.mask(text)
        partial = dict(list(mappings.items())[:1])
        unmasked = engine.unmask(masked, partial)
        # Only the first mapped entity is restored
        for placeholder in partial:
            assert placeholder not in unmasked or partial[placeholder] in unmasked

    def test_placeholder_contains_no_digits(self):
        """Alpha-only placeholders prevent NER regex false matches"""
        from mask_engine import RegexMaskEngine
        engine = RegexMaskEngine()
        masked, _, _ = engine.mask("13812345678")
        import re
        placeholders = re.findall(r'\[PII_\w+_\w+\]', masked)
        for ph in placeholders:
            suffix = ph.split("_")[-1].rstrip("]")
            assert not any(c.isdigit() for c in suffix)

    def test_add_custom_keyword_empty(self):
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        assert engine.add_custom_keyword("") is False

    def test_add_custom_keyword_nonexistent_remove(self):
        from mask_engine import get_mask_engine
        engine = get_mask_engine()
        assert engine.remove_custom_keyword("不存在的关键词") is False
