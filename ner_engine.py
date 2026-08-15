import logging
import os
import re
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

    PERSON = "PER"  # 人名
    LOCATION = "LOC"  # 地名
    ORGANIZATION = "ORG"  # 机构/公司名
    PHONE = "PHONE"  # 手机号
    EMAIL = "EMAIL"  # 邮箱
    IDCARD = "IDCARD"  # 身份证号
    BANKCARD = "BANKCARD"  # 银行卡号
    PLATE = "PLATE"  # 车牌号
    IP = "IP"  # IP地址
    URL = "URL"  # URL链接
    DATE = "DATE"  # 日期
    AMOUNT = "AMOUNT"  # 金额
    POSTCODE = "POSTCODE"  # 邮编
    APIKEY = "APIKEY"  # API 密钥


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
            "end": self.end,
        }


# 常见词停用表：单字姓 + 1~2 字会误判的常用词，规则引擎据此降误报。
_COMMON_WORD_STOPLIST = frozenset(
    {
        "安全",
        "任何",
        "因为",
        "所以",
        "包含",
        "没有",
        "文本",
        "普通",
        "信息",
        "通过",
        "进行",
        "什么",
        "这个",
        "那个",
        "应该",
        "可以",
        "就是",
        "还是",
        "但是",
        "然后",
        "以及",
        "关于",
        "对于",
        "由于",
        "根据",
        "按照",
        "经过",
        "其他",
        "一些",
        "这样",
        "那样",
        "等等",
        "我们",
        "你们",
        "他们",
        "自己",
        "已经",
        "正在",
        "如果",
        "虽然",
    }
)


def _filter_common_words(entities: List[NEREntity]) -> List[NEREntity]:
    """过滤被误判为实体的常见词。"""
    return [e for e in entities if e.value not in _COMMON_WORD_STOPLIST]


class NEREngine:
    """NER 命名实体识别引擎"""

    def __init__(self, model_path: Optional[str] = None):
        self._session = None
        self._tokenizer = None
        self._model_path = model_path or os.environ.get(
            "NER_MODEL_PATH", "./models/ner/model.onnx"
        )
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
        """加载 ONNX NER 模型（接入真实模型的集成点）。

        预期模型接口（标准 BERT 类 NER ONNX 导出）:
          - 输入: input_ids (int64 [batch, seq]), attention_mask (int64 [batch, seq])
          - 输出: logits (float [batch, seq, num_labels])
        需配套同 vocab 的分词器（BERT WordPiece 类），将文本映射为 subword id，
        再按 subword→char 对齐把标签还原为实体区间。

        当前未捆绑模型文件；detect() 始终走规则回退（_detect_by_regex /
        _detect_chinese_names / _detect_locations / _detect_organizations）。
        提供 NER_MODEL_PATH 指向模型文件并实现 _run_onnx() 后即可启用推理。
        """
        if os.path.exists(self._model_path):
            try:
                self._session = ort.InferenceSession(self._model_path)
                logger.info(f"已加载 NER 模型: {self._model_path}")
            except Exception as e:
                logger.warning(f"NER 模型加载失败: {e}，回退规则模式")
                self._session = None
        else:
            logger.info(f"NER 模型文件不存在: {self._model_path}，将使用轻量级规则模式")

    def _tokenize(self, text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
        """分词并保留位置信息"""
        if not HAS_JIEBA:
            return list(text), [(i, i + 1) for i in range(len(text))]

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
            NEREntityType.PHONE: r"(?<!\d)(1[3-9]\d{9})(?!\d)",
            NEREntityType.EMAIL: r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            NEREntityType.IDCARD: r"(?<!\d)([1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)",  # noqa: E501
            NEREntityType.BANKCARD: r"(?<!\d)(\d{16}|\d{19})(?!\d)",
            NEREntityType.PLATE: r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}",
            NEREntityType.IP: r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)",  # noqa: E501
            NEREntityType.URL: r"https?://[^\s]+",
            NEREntityType.DATE: r"\d{4}[-/年](?:0?[1-9]|1[0-2])[-/月](?:0?[1-9]|[12]\d|3[01])日?",
            NEREntityType.AMOUNT: r"(?:¥|￥|\$)\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?",
            NEREntityType.POSTCODE: r"(?<!\d)([1-9]\d{5})(?!\d)",
            NEREntityType.APIKEY: (
                r"\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9]{15,}"
                r"|gh[pousr]_[A-Za-z0-9]{36,}"
                r"|AKIA[0-9A-Z]{16}"
                r"|xox[abp]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,}"
                r"|hf_[A-Za-z0-9]{25,}"
                r"|glpat-[A-Za-z0-9\-_]{20,}"
                r"|AIza[0-9A-Za-z\-_]{35}"
                r"|SG\.[A-Za-z0-9\-_]{22,}\.[A-Za-z0-9\-_]{22,}"
                r"|s[ck]_(?:live|test)_[0-9A-Za-z]{24,}"
                r"|rk_(?:live|test)_[0-9A-Za-z]{24,}"
                r"|ya29\.[0-9A-Za-z\-_]{50,}"
                r"|acct[0-9A-Fa-f]{32}"
                r"|key-[A-Za-z0-9\-_]{20,}"
                r")\b"
            ),
        }

        for entity_type, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                entities.append(
                    NEREntity(
                        entity_type=entity_type,
                        value=match.group(0),
                        start=match.start(),
                        end=match.end(),
                    )
                )

        return entities

    def _detect_chinese_names(self, text: str) -> List[NEREntity]:
        """检测中文人名（基于规则 + jieba）"""
        entities: list[NEREntity] = []

        surname_list = set(
            [
                "赵",
                "钱",
                "孙",
                "李",
                "周",
                "吴",
                "郑",
                "王",
                "冯",
                "陈",
                "褚",
                "卫",
                "蒋",
                "沈",
                "韩",
                "杨",
                "朱",
                "秦",
                "尤",
                "许",
                "何",
                "吕",
                "施",
                "张",
                "孔",
                "曹",
                "严",
                "华",
                "金",
                "魏",
                "陶",
                "姜",
                "戚",
                "谢",
                "邹",
                "喻",
                "柏",
                "水",
                "窦",
                "章",
                "云",
                "苏",
                "潘",
                "葛",
                "奚",
                "范",
                "彭",
                "郎",
                "鲁",
                "韦",
                "昌",
                "马",
                "苗",
                "凤",
                "花",
                "方",
                "俞",
                "任",
                "袁",
                "柳",
                "酆",
                "鲍",
                "史",
                "唐",
                "费",
                "廉",
                "岑",
                "薛",
                "雷",
                "贺",
                "倪",
                "汤",
                "滕",
                "殷",
                "罗",
                "毕",
                "郝",
                "邬",
                "安",
                "常",
                "乐",
                "于",
                "时",
                "傅",
                "皮",
                "卞",
                "齐",
                "康",
                "伍",
                "余",
                "元",
                "卜",
                "顾",
                "孟",
                "平",
                "黄",
                "和",
                "穆",
                "萧",
                "尹",
            ]
        )

        # 复姓（compound surnames）优先检测，避免与单字姓逻辑冲突
        compound_surnames = [
            "欧阳",
            "司马",
            "上官",
            "诸葛",
            "东方",
            "西门",
            "南宫",
            "轩辕",
            "令狐",
            "皇甫",
            "宇文",
            "长孙",
            "慕容",
            "公孙",
            "尉迟",
            "夏侯",
            "司徒",
            "司空",
            "端木",
            "呼延",
            "钟离",
            "百里",
            "东郭",
            "羊舌",
            "宗政",
            "濮阳",
            "独孤",
            "鲜于",
            "闾丘",
            "太史",
            "万俟",
            "闻人",
        ]
        compound_pattern = re.compile(
            "(" + "|".join(compound_surnames) + r")[一-鿿]{1,2}"
        )
        for match in compound_pattern.finditer(text):
            token = match.group()
            entities.append(
                NEREntity(
                    entity_type=NEREntityType.PERSON,
                    value=token,
                    start=match.start(),
                    end=match.end(),
                )
            )

        # Fallback: regex-based detection for Chinese names (surname + 1-2 given name chars).
        # Uses non-greedy matching to prefer 2-char names (surname + 1 given) first.
        # CJK range uses \\u escapes to avoid Windows GBK encoding issues.
        surname_pattern = "[" + "".join(surname_list) + "]"
        pattern = re.compile(surname_pattern + r"[\u4e00-\u9fff]{1,2}?")
        for match in pattern.finditer(text):
            token = match.group()
            start = match.start()
            end = match.end()
            # Exclude matches that are part of longer location-like compounds.
            if any(
                loc in token
                for loc in [
                    "北京",
                    "上海",
                    "天津",
                    "重庆",
                    "省",
                    "市",
                    "区",
                    "县",
                    "路",
                    "街",
                ]
            ):
                continue
            entities.append(
                NEREntity(
                    entity_type=NEREntityType.PERSON, value=token, start=start, end=end
                )
            )

        if not HAS_JIEBA:
            return self._dedup_entities(_filter_common_words(entities))

        tokens, positions = self._tokenize(text)

        for i, (token, pos) in enumerate(zip(tokens, positions)):
            if len(token) == 1 and token in surname_list:
                if i + 1 < len(tokens) and len(tokens[i + 1]) == 1:
                    full_name = token + tokens[i + 1]
                    entities.append(
                        NEREntity(
                            entity_type=NEREntityType.PERSON,
                            value=full_name,
                            start=pos[0],
                            end=positions[i + 1][1],
                        )
                    )
                elif (
                    i + 2 < len(tokens)
                    and len(tokens[i + 1]) == 1
                    and len(tokens[i + 2]) == 1
                ):
                    full_name = token + tokens[i + 1] + tokens[i + 2]
                    entities.append(
                        NEREntity(
                            entity_type=NEREntityType.PERSON,
                            value=full_name,
                            start=pos[0],
                            end=positions[i + 2][1],
                        )
                    )
            elif 2 <= len(token) <= 3 and token[0] in surname_list:
                entities.append(
                    NEREntity(
                        entity_type=NEREntityType.PERSON,
                        value=token,
                        start=pos[0],
                        end=pos[1],
                    )
                )

        return _filter_common_words(entities)

    def _detect_locations(self, text: str) -> List[NEREntity]:
        """检测地名（基于规则）"""
        entities = []

        province_list = [
            "北京",
            "天津",
            "河北",
            "山西",
            "内蒙古",
            "辽宁",
            "吉林",
            "黑龙江",
            "上海",
            "江苏",
            "浙江",
            "安徽",
            "福建",
            "江西",
            "山东",
            "河南",
            "湖北",
            "湖南",
            "广东",
            "广西",
            "海南",
            "重庆",
            "四川",
            "贵州",
            "云南",
            "西藏",
            "陕西",
            "甘肃",
            "青海",
            "宁夏",
            "新疆",
            "香港",
            "澳门",
            "台湾",
        ]

        city_suffixes = ["市", "区", "县", "镇", "乡", "村", "街道", "路", "巷"]
        area_suffixes = ["省", "自治区", "直辖市", "特别行政区"]

        for province in province_list:
            if province in text:
                start = text.index(province)
                entities.append(
                    NEREntity(
                        entity_type=NEREntityType.LOCATION,
                        value=province,
                        start=start,
                        end=start + len(province),
                    )
                )

        tokens, positions = self._tokenize(text)

        for token, pos in zip(tokens, positions):
            if any(suffix in token for suffix in city_suffixes + area_suffixes):
                entities.append(
                    NEREntity(
                        entity_type=NEREntityType.LOCATION,
                        value=token,
                        start=pos[0],
                        end=pos[1],
                    )
                )

        return entities

    def _detect_organizations(self, text: str) -> List[NEREntity]:
        """检测机构名（基于规则：名称 + 机构后缀）。"""
        entities = []
        # 后缀按长度降序，避免短后缀（'公司'）在长后缀（'有限公司'）之前匹配
        org_suffixes = sorted(
            [
                "股份有限公司",
                "有限责任公司",
                "有限公司",
                "集团公司",
                "公司",
                "集团",
                "银行",
                "大学",
                "学院",
                "医院",
                "研究院",
                "研究所",
                "事务所",
                "中心",
                "协会",
                "委员会",
                "基金会",
                "合作社",
                "学校",
                "出版社",
                "电视台",
                "证券",
                "保险",
            ],
            key=len,
            reverse=True,
        )
        pattern = re.compile(r"([一-鿿]{2,12}?)(?:" + "|".join(org_suffixes) + ")")
        for match in pattern.finditer(text):
            name = match.group(1)
            full = match.group()
            if len(name) < 2:
                continue
            # 排除明显非机构名（名称全是地名常见字/方位词）
            if all(ch in "东西南北中上下左右前后" for ch in name):
                continue
            entities.append(
                NEREntity(
                    entity_type=NEREntityType.ORGANIZATION,
                    value=full,
                    start=match.start(),
                    end=match.end(),
                )
            )
        return entities

    def detect(self, text: str) -> List[NEREntity]:
        """检测文本中的实体（纯规则模式）。

        ONNX 模型仅作未来扩展预留；当前未捆绑模型文件，检测始终走规则回退。
        """
        entities = []
        entities.extend(self._detect_by_regex(text))
        entities.extend(self._detect_chinese_names(text))
        entities.extend(self._detect_locations(text))
        entities.extend(self._detect_organizations(text))

        entities = self._remove_overlaps(entities)
        return entities

    def _dedup_entities(self, entities: List[NEREntity]) -> List[NEREntity]:
        """Remove duplicate entities (same value and position)."""
        seen: set[tuple[int, int, str]] = set()
        result: list[NEREntity] = []
        for e in entities:
            key = (e.start, e.end, e.value)
            if key not in seen:
                seen.add(key)
                result.append(e)
        return result

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
