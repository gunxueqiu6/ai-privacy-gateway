import logging
import os
from typing import List, Dict, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)

try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False
    logger.warning("jieba not installed, Chinese NER may be limited")

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False
    logger.warning("onnxruntime not installed, NER model disabled")


class NEREntityType(Enum):
    """NER 实体类型"""
    PERSON = "PER"           # 人名
    LOCATION = "LOC"         # 地名
    ORGANIZATION = "ORG"     # 机构/公司名
    PHONE = "PHONE"          # 手机号
    EMAIL = "EMAIL"          # 邮箱
    IDCARD = "IDCARD"        # 身份证号
    BANKCARD = "BANKCARD"    # 银行卡号
    PLATE = "PLATE"          # 车牌号
    IP = "IP"                # IP地址
    URL = "URL"              # URL链接
    DATE = "DATE"            # 日期
    AMOUNT = "AMOUNT"        # 金额
    POSTCODE = "POSTCODE"    # 邮编


class NEREntity:
    """NER 实体结果"""
    
    def __init__(self, entity_type: NEREntityType, value: str, start: int, end: int):
        self.entity_type = entity_type
        self.value = value
        self.start = start
        self.end = end
    
    def to_dict(self) -> Dict:
        return {
            "type": self.entity_type.value,
            "value": self.value,
            "start": self.start,
            "end": self.end
        }


class NEREngine:
    """NER 命名实体识别引擎"""
    
    def __init__(self, model_path: Optional[str] = None):
        self._session = None
        self._tokenizer = None
        self._model_path = model_path or os.environ.get("NER_MODEL_PATH", "./models/ner/model.onnx")
        self._is_enabled = HAS_ONNX and HAS_JIEBA
        self._supported_types = set(NEREntityType)
        
        if self._is_enabled:
            try:
                self._load_model()
                logger.info("✅ NER 引擎初始化完成")
            except Exception as e:
                logger.warning(f"NER 模型加载失败: {e}, 将使用正则模式")
                self._is_enabled = False
    
    @property
    def is_enabled(self) -> bool:
        return self._is_enabled
    
    def _load_model(self):
        """加载 ONNX NER 模型"""
        if os.path.exists(self._model_path):
            self._session = ort.InferenceSession(self._model_path)
        else:
            logger.info(f"NER 模型文件不存在: {self._model_path}，将使用轻量级模式")
    
    def _tokenize(self, text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        """分词并保留位置信息"""
        if not HAS_JIEBA:
            return list(text), [(i, i+1) for i in range(len(text))]
        
        tokens = []
        positions = []
        
        for word in jieba.tokenize(text):
            tokens.append(word[0])
            positions.append((word[1], word[2]))
        
        return tokens, positions
    
    def _detect_by_regex(self, text: str) -> List[NEREntity]:
        """使用正则表达式检测实体（fallback 模式）"""
        import re
        entities = []
        
        patterns = {
            NEREntityType.PHONE: r'(?<!\d)(1[3-9]\d{9})(?!\d)',
            NEREntityType.EMAIL: r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            NEREntityType.IDCARD: r'(?<!\d)([1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)',
            NEREntityType.BANKCARD: r'(?<!\d)(\d{16}|\d{19})(?!\d)',
            NEREntityType.PLATE: r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}',
            NEREntityType.IP: r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',
            NEREntityType.URL: r'https?://[^\s]+',
            NEREntityType.DATE: r'\d{4}[-/年](?:0?[1-9]|1[0-2])[-/月](?:0?[1-9]|[12]\d|3[01])日?',
            NEREntityType.AMOUNT: r'(?:¥|￥|\\$|\\$)?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?',
            NEREntityType.POSTCODE: r'(?<!\d)([1-9]\d{5})(?!\d)',
        }
        
        for entity_type, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                entities.append(NEREntity(
                    entity_type=entity_type,
                    value=match.group(0),
                    start=match.start(),
                    end=match.end()
                ))
        
        return entities
    
    def _detect_chinese_names(self, text: str) -> List[NEREntity]:
        """检测中文人名（基于规则）"""
        entities: list[NEREntity] = []
        if not HAS_JIEBA:
            return entities
        
        tokens, positions = self._tokenize(text)
        
        surname_list = set([
            '赵', '钱', '孙', '李', '周', '吴', '郑', '王', '冯', '陈',
            '褚', '卫', '蒋', '沈', '韩', '杨', '朱', '秦', '尤', '许',
            '何', '吕', '施', '张', '孔', '曹', '严', '华', '金', '魏',
            '陶', '姜', '戚', '谢', '邹', '喻', '柏', '水', '窦', '章',
            '云', '苏', '潘', '葛', '奚', '范', '彭', '郎', '鲁', '韦',
            '昌', '马', '苗', '凤', '花', '方', '俞', '任', '袁', '柳',
            '酆', '鲍', '史', '唐', '费', '廉', '岑', '薛', '雷', '贺',
            '倪', '汤', '滕', '殷', '罗', '毕', '郝', '邬', '安', '常',
            '乐', '于', '时', '傅', '皮', '卞', '齐', '康', '伍', '余',
            '元', '卜', '顾', '孟', '平', '黄', '和', '穆', '萧', '尹'
        ])
        
        for i, (token, pos) in enumerate(zip(tokens, positions)):
            if len(token) == 1 and token in surname_list:
                if i + 1 < len(tokens) and len(tokens[i+1]) == 1:
                    full_name = token + tokens[i+1]
                    entities.append(NEREntity(
                        entity_type=NEREntityType.PERSON,
                        value=full_name,
                        start=pos[0],
                        end=positions[i+1][1]
                    ))
                elif i + 2 < len(tokens) and len(tokens[i+1]) == 1 and len(tokens[i+2]) == 1:
                    full_name = token + tokens[i+1] + tokens[i+2]
                    entities.append(NEREntity(
                        entity_type=NEREntityType.PERSON,
                        value=full_name,
                        start=pos[0],
                        end=positions[i+2][1]
                    ))
            elif 2 <= len(token) <= 3 and token[0] in surname_list:
                entities.append(NEREntity(
                    entity_type=NEREntityType.PERSON,
                    value=token,
                    start=pos[0],
                    end=pos[1]
                ))
        
        return entities
    
    def _detect_locations(self, text: str) -> List[NEREntity]:
        """检测地名（基于规则）"""
        entities = []
        
        province_list = [
            '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
            '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
            '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
            '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆', '香港', '澳门', '台湾'
        ]
        
        city_suffixes = ['市', '区', '县', '镇', '乡', '村', '街道', '路', '巷']
        area_suffixes = ['省', '自治区', '直辖市', '特别行政区']
        
        for province in province_list:
            if province in text:
                start = text.index(province)
                entities.append(NEREntity(
                    entity_type=NEREntityType.LOCATION,
                    value=province,
                    start=start,
                    end=start + len(province)
                ))
        
        tokens, positions = self._tokenize(text)
        
        for token, pos in zip(tokens, positions):
            if any(suffix in token for suffix in city_suffixes + area_suffixes):
                entities.append(NEREntity(
                    entity_type=NEREntityType.LOCATION,
                    value=token,
                    start=pos[0],
                    end=pos[1]
                ))
        
        return entities
    
    def detect(self, text: str) -> List[NEREntity]:
        """检测文本中的实体"""
        entities = []
        
        if self._session:
            pass
        else:
            entities.extend(self._detect_by_regex(text))
            entities.extend(self._detect_chinese_names(text))
            entities.extend(self._detect_locations(text))
        
        entities = self._remove_overlaps(entities)
        return entities
    
    def _remove_overlaps(self, entities: List[NEREntity]) -> List[NEREntity]:
        """移除重叠的实体（保留较长的）"""
        if not entities:
            return []
        
        sorted_entities = sorted(entities, key=lambda e: (e.start, -(e.end - e.start)))
        result: list[NEREntity] = []
        
        for entity in sorted_entities:
            is_overlapping = False
            for existing in result:
                if not (entity.end <= existing.start or entity.start >= existing.end):
                    is_overlapping = True
                    break
            if not is_overlapping:
                result.append(entity)
        
        return sorted(result, key=lambda e: e.start)
    
    def get_supported_types(self) -> List[str]:
        """获取支持的实体类型"""
        return [t.value for t in self._supported_types]


_ner_engine: Optional[NEREngine] = None


def get_ner_engine() -> NEREngine:
    """获取 NER 引擎实例"""
    global _ner_engine
    if _ner_engine is None:
        _ner_engine = NEREngine()
    return _ner_engine