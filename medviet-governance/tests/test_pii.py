# tests/test_pii.py
import pytest
import pandas as pd
from src.pii.anonymizer import MedVietAnonymizer

@pytest.fixture(scope="module")
def anonymizer():
    return MedVietAnonymizer()

@pytest.fixture
def sample_df():
    # cccd & so_dien_thoai phải đọc dạng str để giữ số 0 đầu (định danh, không phải số)
    return pd.read_csv(
        "data/raw/patients_raw.csv",
        dtype={"cccd": str, "so_dien_thoai": str},
    ).head(50)

class TestPIIDetection:

    def test_cccd_detected(self, anonymizer):
        text = "Bệnh nhân Nguyen Van A, CCCD: 012345678901"
        results = anonymizer.analyzer.analyze(text=text, language="vi",
                                               entities=["VN_CCCD"])
        assert len(results) >= 1
        assert any(r.entity_type == "VN_CCCD" for r in results)

    def test_phone_detected(self, anonymizer):
        text = "Liên hệ: 0912345678"
        results = anonymizer.analyzer.analyze(text=text, language="vi",
                                              entities=["VN_PHONE"])
        assert len(results) >= 1
        assert any(r.entity_type == "VN_PHONE" for r in results)

    def test_email_detected(self, anonymizer):
        text = "Email: nguyenvana@gmail.com"
        results = anonymizer.analyzer.analyze(text=text, language="vi",
                                              entities=["EMAIL_ADDRESS"])
        assert len(results) >= 1
        assert any(r.entity_type == "EMAIL_ADDRESS" for r in results)

    # --- TASK QUAN TRỌNG ---
    def test_detection_rate_above_95_percent(self, anonymizer, sample_df):
        """Pipeline phải đạt >95% detection rate."""
        pii_columns = ["ho_ten", "cccd", "so_dien_thoai", "email"]
        rate = anonymizer.calculate_detection_rate(sample_df, pii_columns)
        print(f"\nDetection rate: {rate:.2%}")
        assert rate >= 0.95, f"Detection rate {rate:.2%} < 95%"

class TestAnonymization:

    def test_pii_not_in_output(self, anonymizer, sample_df):
        """Sau anonymization, không còn CCCD gốc trong output."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        output_blob = df_anon.astype(str).to_csv(index=False)
        for original_cccd in sample_df["cccd"]:
            assert str(original_cccd) not in output_blob

    def test_non_pii_columns_unchanged(self, anonymizer, sample_df):
        """Cột benh và ket_qua_xet_nghiem phải giữ nguyên."""
        df_anon = anonymizer.anonymize_dataframe(sample_df)
        assert df_anon["benh"].tolist() == sample_df["benh"].tolist()
        assert df_anon["ket_qua_xet_nghiem"].tolist() == \
            sample_df["ket_qua_xet_nghiem"].tolist()
