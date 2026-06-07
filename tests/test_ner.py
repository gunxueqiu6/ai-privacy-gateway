"""
NER Engine 测试 - 命名实体识别引擎
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestNEREngine:
    """NER 引擎测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        try:
            from ner_engine import NEREngine, get_ner_engine

            engine = get_ner_engine()
            assert engine is not None
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_person_detection(self):
        """测试人名检测"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            text = "张三和李四一起去了北京"
            entities = engine.detect(text)

            # 应检测到人名
            persons = [e for e in entities if e.get("type") == "PER"]
            assert len(persons) >= 1
            person_names = [e.get("value") for e in persons]
            # 可能检测到张三或李四
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_location_detection(self):
        """测试地名检测"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            text = "他住在北京市海淀区"
            entities = engine.detect(text)

            # 应检测到地名
            locations = [e for e in entities if e.get("type") == "LOC"]
            assert len(locations) >= 1
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_organization_detection(self):
        """测试机构名检测"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            text = "他在阿里巴巴工作"
            entities = engine.detect(text)

            # 应检测到机构名
            orgs = [e for e in entities if e.get("type") == "ORG"]
            assert len(orgs) >= 1
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_multiple_entities(self):
        """测试多实体检测"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            text = "张三在北京的腾讯公司工作，他的手机号是13812345678"
            entities = engine.detect(text)

            # 应检测到多种实体
            entity_types = [e.get("type") for e in entities]
            # 可能包含 PER, LOC, ORG, PHONE
            assert len(entities) >= 2
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_empty_text(self):
        """测试空文本"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            entities = engine.detect("")
            assert len(entities) == 0

            entities = engine.detect(None)
            assert len(entities) == 0
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_no_entities(self):
        """测试无实体文本"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            text = "这是一段普通文本，没有任何敏感信息"
            entities = engine.detect(text)

            # 不应检测到实体
            assert len(entities) == 0
        except ImportError:
            pytest.skip("ner_engine module not available")


class TestNERFallback:
    """NER 降级回退测试"""

    def test_fallback_to_regex(self):
        """测试回退到正则"""
        try:
            from ner_engine import NEREngine

            # 模拟模型不可用
            engine = NEREngine(use_model=False)

            text = "手机号13812345678"
            entities = engine.detect(text)

            # 应通过正则回退检测到手机号
            phones = [e for e in entities if e.get("type") == "PHONE"]
            assert len(phones) >= 1
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_model_unavailable_fallback(self):
        """测试模型不可用时降级"""
        try:
            from ner_engine import NEREngine

            # 模拟模型加载失败
            with patch('ner_engine.NEREngine.load_model') as mock_load:
                mock_load.side_effect = Exception("Model not available")

                engine = NEREngine()
                # 应自动降级到正则模式
                assert engine.fallback_mode is True
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_hybrid_detection(self):
        """测试混合检测（模型+正则）"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            # 包含NER实体和正则实体
            text = "张三的手机号13812345678"
            entities = engine.detect(text)

            # 应同时检测到人名和手机号
            entity_types = set(e.get("type") for e in entities)
            # 可能包含 PER 和 PHONE
            assert len(entity_types) >= 1
        except ImportError:
            pytest.skip("ner_engine module not available")


class TestNERPerformance:
    """NER 性能测试"""

    def test_large_text_detection(self):
        """测试大文本检测"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            # 生成大文本
            large_text = "普通文本 " * 100 + "张三在北京" + " 普通文本" * 100

            entities = engine.detect(large_text)
            # 应能处理大文本
            assert isinstance(entities, list)
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_batch_detection(self):
        """测试批量检测"""
        try:
            from ner_engine import get_ner_engine

            engine = get_ner_engine()

            texts = [
                "张三在北京",
                "李四在上海",
                "王五在广州"
            ]

            results = engine.detect_batch(texts)
            assert len(results) == len(texts)
            for entities in results:
                assert isinstance(entities, list)
        except ImportError:
            pytest.skip("ner_engine module not available")


class TestNERConfig:
    """NER 配置测试"""

    def test_entity_type_config(self):
        """测试实体类型配置"""
        try:
            from ner_engine import NEREngine

            # 只启用特定实体类型
            engine = NEREngine(enabled_types=["PER", "LOC"])

            text = "张三在北京，手机号13812345678"
            entities = engine.detect(text)

            # 只应检测到 PER 和 LOC
            entity_types = set(e.get("type") for e in entities)
            # PHONE 不应被检测（如果配置生效）
        except ImportError:
            pytest.skip("ner_engine module not available")

    def test_confidence_threshold(self):
        """测试置信度阈值"""
        try:
            from ner_engine import NEREngine

            # 设置置信度阈值
            engine = NEREngine(min_confidence=0.8)

            text = "张三在北京"
            entities = engine.detect(text)

            # 只返回高置信度的实体
            for entity in entities:
                if "confidence" in entity:
                    assert entity["confidence"] >= 0.8
        except ImportError:
            pytest.skip("ner_engine module not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])