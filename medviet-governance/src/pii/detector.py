# src/pii/detector.py
"""PII detection cho tiếng Việt dùng Presidio.

Chiến lược: custom PatternRecognizer cho CCCD / phone / email / person (đăng ký
dưới language="vi"). NLP engine dùng spaCy vi model nếu có; nếu không có thì
fallback sang spaCy blank("vi"). Pattern recognizers đủ để đạt detection rate
>95% mà không cần tải model NER nặng vi_core_news_lg.
"""
from pathlib import Path

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider

VI_LANGUAGE = "vi"
VI_MODEL_CANDIDATES = ("vi_core_news_lg", "vi_spacy_model")
SUPPORTED_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "VN_CCCD", "VN_PHONE"]

# Regex cho tên người VN (chữ Latin có dấu) — dùng khi spaCy NER không có.
_VN_UPPER = (
    "A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨ"
    "ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ"
)
_VN_LOWER = (
    "a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩ"
    "òóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
)


def _resolve_vi_model_name() -> str:
    """Trả về tên model spaCy vi đã cài, hoặc "" nếu không có."""
    import spacy

    for name in VI_MODEL_CANDIDATES:
        try:
            spacy.load(name)
            return name
        except OSError:
            continue
    return ""


def _blank_vi_model_path() -> str:
    """Tạo (cache) blank spaCy vi model trên disk, trả về path.

    use_pyvi=False để không phụ thuộc package pyvi — PII detection dựa trên
    PatternRecognizer (regex), không cần tokenizer tiếng Việt chất lượng cao.
    """
    import spacy

    blank_path = Path.cwd() / ".spacy_models" / "vi_blank"
    if not blank_path.exists():
        blank_path.parent.mkdir(parents=True, exist_ok=True)
        nlp = spacy.blank("vi", config={"nlp": {"tokenizer": {"use_pyvi": False}}})
        nlp.to_disk(blank_path)
    return str(blank_path)


def build_vietnamese_analyzer() -> AnalyzerEngine:
    """Xây dựng AnalyzerEngine với các recognizer tùy chỉnh cho VN."""

    # --- TASK 2.2.1 --- CCCD: đúng 12 chữ số
    cccd_pattern = Pattern(
        name="cccd_pattern",
        regex=r"\b\d{12}\b",
        score=0.9,
    )
    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        supported_language=VI_LANGUAGE,
        patterns=[cccd_pattern],
        context=["cccd", "căn cước", "chứng minh", "cmnd"],
    )

    # --- TASK 2.2.2 --- Phone VN: 0[3|5|7|8|9] + 8 chữ số
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        supported_language=VI_LANGUAGE,
        patterns=[Pattern(
            name="vn_phone",
            regex=r"\b0[35789]\d{8}\b",
            score=0.85,
        )],
        context=["điện thoại", "sdt", "phone", "liên hệ"],
    )

    # Email recognizer (đăng ký dưới "vi" — built-in EmailRecognizer chỉ có "en")
    email_recognizer = PatternRecognizer(
        supported_entity="EMAIL_ADDRESS",
        supported_language=VI_LANGUAGE,
        patterns=[Pattern(
            name="email_pattern",
            regex=r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
            score=0.9,
        )],
        context=["email", "mail", "gmail"],
    )

    # Person recognizer (pattern) — fallback khi không có spaCy NER vi
    person_recognizer = PatternRecognizer(
        supported_entity="PERSON",
        supported_language=VI_LANGUAGE,
        patterns=[Pattern(
            name="vn_person_latin",
            regex=(
                rf"\b[{_VN_UPPER}][{_VN_LOWER}]+"
                rf"(?:\s+[{_VN_UPPER}][{_VN_LOWER}]+){{1,3}}\b"
            ),
            score=0.6,
        )],
    )

    # --- TASK 2.2.3 --- NLP engine dùng spaCy vi model (hoặc blank fallback)
    model_name = _resolve_vi_model_name() or _blank_vi_model_path()
    provider = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": VI_LANGUAGE, "model_name": model_name}],
    })
    nlp_engine = provider.create_engine()

    # --- TASK 2.2.4 --- Khởi tạo AnalyzerEngine + add recognizers
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=[VI_LANGUAGE],
    )
    analyzer.registry.add_recognizer(cccd_recognizer)
    analyzer.registry.add_recognizer(phone_recognizer)
    analyzer.registry.add_recognizer(email_recognizer)
    analyzer.registry.add_recognizer(person_recognizer)

    return analyzer


def detect_pii(text: str, analyzer: AnalyzerEngine) -> list:
    """Detect PII trong text tiếng Việt. Trả về list RecognizerResult.

    Entities: PERSON, EMAIL_ADDRESS, VN_CCCD, VN_PHONE.
    """
    results = analyzer.analyze(
        text=text,
        language=VI_LANGUAGE,
        entities=SUPPORTED_ENTITIES,
    )
    return results
