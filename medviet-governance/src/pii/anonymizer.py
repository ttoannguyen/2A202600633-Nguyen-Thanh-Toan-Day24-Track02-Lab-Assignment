# src/pii/anonymizer.py
import random

import pandas as pd
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from faker import Faker

from .detector import build_vietnamese_analyzer, detect_pii

fake = Faker("vi_VN")


def fake_cccd() -> str:
    """CCCD giả: đúng 12 chữ số."""
    return "".join(str(random.randint(0, 9)) for _ in range(12))


def fake_phone() -> str:
    """Số điện thoại VN giả: 0[3|5|7|8|9] + 8 chữ số."""
    return "0" + str(random.choice([3, 5, 7, 8, 9])) + \
        "".join(str(random.randint(0, 9)) for _ in range(8))


class MedVietAnonymizer:

    def __init__(self):
        self.analyzer = build_vietnamese_analyzer()
        self.anonymizer = AnonymizerEngine()

    def anonymize_text(self, text: str, strategy: str = "replace") -> str:
        """Anonymize text với strategy được chọn.

        Strategies:
        - "mask"    : Nguyen Van A -> N****** V** A
        - "replace" : thay bằng fake data (Faker)
        - "hash"    : SHA-256 one-way hash
        """
        results = detect_pii(text, self.analyzer)
        if not results:
            return text

        if strategy == "replace":
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": fake.name()}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": fake.email()}),
                "VN_CCCD": OperatorConfig("replace", {"new_value": fake_cccd()}),
                "VN_PHONE": OperatorConfig("replace", {"new_value": fake_phone()}),
            }
        elif strategy == "mask":
            # Mask: giữ vài ký tự đầu, thay phần còn lại bằng '*'
            operators = {
                "DEFAULT": OperatorConfig("mask", {
                    "masking_char": "*",
                    "chars_to_mask": 100,   # mask tối đa; from_end=False giữ ký tự đầu
                    "from_end": False,
                }),
            }
        elif strategy == "hash":
            operators = {
                "DEFAULT": OperatorConfig("hash", {"hash_type": "sha256"}),
            }
        else:
            operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"})}

        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        return anonymized.text

    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Anonymize toàn bộ DataFrame.

        - ho_ten, dia_chi, email, bac_si_phu_trach: thay bằng fake data
        - cccd, so_dien_thoai: thay trực tiếp bằng fake data
        - ngay_sinh: generalize -> chỉ giữ năm sinh
        - benh, ket_qua_xet_nghiem: GIỮ NGUYÊN (cần cho model training)
        - patient_id: GIỮ NGUYÊN (pseudonym đã đủ an toàn)
        """
        df_anon = df.copy()

        if "ho_ten" in df_anon:
            df_anon["ho_ten"] = [fake.name() for _ in range(len(df_anon))]
        if "bac_si_phu_trach" in df_anon:
            df_anon["bac_si_phu_trach"] = [fake.name() for _ in range(len(df_anon))]
        if "dia_chi" in df_anon:
            df_anon["dia_chi"] = [fake.address().replace("\n", ", ") for _ in range(len(df_anon))]
        if "email" in df_anon:
            df_anon["email"] = [fake.email() for _ in range(len(df_anon))]
        if "cccd" in df_anon:
            df_anon["cccd"] = [fake_cccd() for _ in range(len(df_anon))]
        if "so_dien_thoai" in df_anon:
            df_anon["so_dien_thoai"] = [fake_phone() for _ in range(len(df_anon))]
        if "ngay_sinh" in df_anon:
            # generalize: dd/mm/yyyy -> yyyy
            df_anon["ngay_sinh"] = df_anon["ngay_sinh"].astype(str).str.split("/").str[-1]

        return df_anon

    def calculate_detection_rate(self,
                                 original_df: pd.DataFrame,
                                 pii_columns: list) -> float:
        """Tính % PII được detect thành công. Mục tiêu: > 95%.

        Với mỗi ô trong pii_columns, kiểm tra detect_pii() tìm thấy >=1 entity.
        """
        total = 0
        detected = 0

        for col in pii_columns:
            for value in original_df[col].astype(str):
                total += 1
                results = detect_pii(value, self.analyzer)
                if len(results) > 0:
                    detected += 1

        return detected / total if total > 0 else 0.0
