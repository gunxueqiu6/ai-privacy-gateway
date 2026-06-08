"""
NER Engine 测试 — 命名实体识别引擎
"""
import pytest
from unittest.mock import patch


def _detected_types(entities):
    """从 NEREntity 列表中提取类型字符串"""
    return [e.entity_type.value for e in entities]


class TestNEREngine:
    """NER 引擎测试"""

    def test_engine_initialization(self):
        """测试引擎初始化"""
        from ner_engine import NEREngine, get_ner_engine
        engine = get_ner_engine()
        assert engine is not None

    def test_phone_detection(self):
        """测试手机号检测（正则）"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        entities = engine.detect("手机号13812345678")
        types = _detected_types(entities)
        assert "PHONE" in types

    def test_email_detection(self):
        """测试邮箱检测（正则）"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        entities = engine.detect("邮箱 test@example.com")
        types = _detected_types(entities)
        assert "EMAIL" in types

    def test_person_detection(self):
        """测试中文人名检测"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        entities = engine.detect("张三和李四一起去了北京")
        types = _detected_types(entities)
        assert "PER" in types

    def test_location_detection(self):
        """测试地名检测"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        entities = engine.detect("他住在北京市海淀区")
        types = _detected_types(entities)
        assert "LOC" in types

    def test_multiple_entities(self):
        """测试多实体检测"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        entities = engine.detect("张三在北京，手机号13812345678，邮箱test@x.com")
        types = _detected_types(entities)
        # 至少应检测到 2 种实体类型
        assert len(set(types)) >= 2

    def test_empty_text(self):
        """测试空文本"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        entities = engine.detect("")
        assert len(entities) == 0

    def test_no_entities(self):
        """测试无实体文本"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        entities = engine.detect("这是一段普通文本没有敏感信息")
        assert len(entities) == 0

    def test_nerentity_to_dict(self):
        """NEREntity.to_dict() 返回正确结构"""
        from ner_engine import NEREntity, NEREntityType
        e = NEREntity(NEREntityType.PERSON, "张三", 0, 2)
        d = e.to_dict()
        assert d["type"] == "PER"
        assert d["value"] == "张三"
        assert d["start"] == 0
        assert d["end"] == 2


class TestNERFallback:
    """NER 降级回退测试"""

    def test_regex_fallback_for_phone(self):
        """模型不可用时正则仍可检测手机号"""
        from ner_engine import NEREngine
        # 不提供 model_path 时默认路径不存在模型文件，使用正则 fallback
        engine = NEREngine(model_path="/nonexistent/model.onnx")
        entities = engine.detect("手机号13812345678")
        types = _detected_types(entities)
        assert "PHONE" in types

    def test_model_load_failure_does_not_crash(self):
        """模型加载失败时不崩溃，回退到正则模式"""
        from ner_engine import NEREngine
        with patch.object(NEREngine, '_load_model', side_effect=Exception("Load failed")):
            engine = NEREngine()
            # 应能正常使用正则 fallback
            entities = engine.detect("13812345678")
            types = _detected_types(entities)
            assert "PHONE" in types


class TestNERGetSupportedTypes:
    """get_supported_types 测试"""

    def test_get_supported_types(self):
        """返回所有支持的实体类型"""
        from ner_engine import get_ner_engine
        engine = get_ner_engine()
        types = engine.get_supported_types()
        assert "PER" in types
        assert "LOC" in types
        assert "PHONE" in types
        assert "EMAIL" in types
