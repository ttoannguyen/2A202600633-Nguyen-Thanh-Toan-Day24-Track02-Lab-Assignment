# src/quality/validation.py
import os

import pandas as pd

EMAIL_REGEX = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
VALID_CONDITIONS = ["Tiểu đường", "Huyết áp cao", "Tim mạch", "Khỏe mạnh"]
RAW_CSV = "data/raw/patients_raw.csv"
# cccd & so_dien_thoai là định danh — đọc dạng str để giữ số 0 đầu
ID_DTYPES = {"cccd": str, "so_dien_thoai": str}


def build_patient_expectation_suite():
    """Tạo expectation suite cho patient data (Great Expectations Fluent API).

    Lưu ý: API GX thay đổi nhiều giữa các version. Hàm này viết theo API 0.17.x
    Fluent. Nếu môi trường dùng GX khác, dùng validate_anonymized_data() (thuần
    pandas) để chấm điểm phần data quality.
    """
    import great_expectations as gx

    context = gx.get_context()
    suite = context.add_expectation_suite("patient_data_suite")

    df = pd.read_csv(RAW_CSV, dtype=ID_DTYPES)
    validator = context.sources.pandas_default.read_dataframe(df)

    # 1. patient_id không được null
    validator.expect_column_values_to_not_be_null("patient_id")

    # 2. cccd phải có đúng 12 ký tự
    validator.expect_column_value_lengths_to_equal(
        column="cccd",
        value=12,
    )

    # 3. ket_qua_xet_nghiem trong khoảng [0, 50]
    validator.expect_column_values_to_be_between(
        column="ket_qua_xet_nghiem",
        min_value=0,
        max_value=50,
    )

    # 4. benh phải thuộc danh sách hợp lệ
    validator.expect_column_values_to_be_in_set(
        column="benh",
        value_set=VALID_CONDITIONS,
    )

    # 5. email match regex
    validator.expect_column_values_to_match_regex(
        column="email",
        regex=r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    )

    # 6. patient_id không trùng
    validator.expect_column_values_to_be_unique(column="patient_id")

    validator.save_expectation_suite()
    return suite


def validate_patient_dataframe(df: pd.DataFrame) -> dict:
    """Chạy bộ expectations thuần pandas trên 1 DataFrame.

    Trả về {"success": bool, "failed_checks": [str], "stats": dict}.
    Dùng cho chấm điểm không phụ thuộc version Great Expectations.
    """
    failed = []

    # patient_id không null
    if df["patient_id"].isnull().any():
        failed.append("patient_id has null values")
    # patient_id unique
    if df["patient_id"].duplicated().any():
        failed.append("patient_id has duplicates")
    # cccd đúng 12 ký tự
    if not df["cccd"].astype(str).str.len().eq(12).all():
        failed.append("cccd length != 12")
    # ket_qua trong [0, 50]
    kq = pd.to_numeric(df["ket_qua_xet_nghiem"], errors="coerce")
    if not kq.between(0, 50).all():
        failed.append("ket_qua_xet_nghiem out of range [0,50]")
    # benh trong set hợp lệ
    if not df["benh"].isin(VALID_CONDITIONS).all():
        failed.append("benh has invalid values")
    # email match regex
    if not df["email"].astype(str).str.match(EMAIL_REGEX).all():
        failed.append("email format invalid")

    return {
        "success": len(failed) == 0,
        "failed_checks": failed,
        "stats": {"total_rows": len(df), "columns": list(df.columns)},
    }


def validate_anonymized_data(filepath: str, raw_filepath: str = RAW_CSV) -> dict:
    """Validate anonymized data (thuần pandas).

    Trả về dict: {"success": bool, "failed_checks": list, "stats": dict}.
    """
    df = pd.read_csv(filepath, dtype=ID_DTYPES)
    results = {
        "success": True,
        "failed_checks": [],
        "stats": {
            "total_rows": len(df),
            "columns": list(df.columns),
        },
    }

    # Check 1: Không còn CCCD gốc trong output
    if os.path.exists(raw_filepath) and "cccd" in df.columns:
        raw = pd.read_csv(raw_filepath, dtype=ID_DTYPES)
        raw_cccd = set(raw["cccd"].astype(str))
        anon_cccd = set(df["cccd"].astype(str))
        leaked = raw_cccd & anon_cccd
        if leaked:
            results["failed_checks"].append(
                f"{len(leaked)} CCCD gốc còn trong output"
            )

    # Check 2: Không có null trong các cột quan trọng
    important = [c for c in ("patient_id", "benh") if c in df.columns]
    for col in important:
        if df[col].isnull().any():
            results["failed_checks"].append(f"null trong cột {col}")

    # Check 3: Số rows bằng original
    if os.path.exists(raw_filepath):
        raw_rows = len(pd.read_csv(raw_filepath))
        if len(df) != raw_rows:
            results["failed_checks"].append(
                f"row count {len(df)} != original {raw_rows}"
            )

    results["success"] = len(results["failed_checks"]) == 0
    return results
