# src/api/main.py
from fastapi import FastAPI, Depends, HTTPException
import pandas as pd
from src.access.rbac import get_current_user, require_permission
from src.pii.anonymizer import MedVietAnonymizer

app = FastAPI(title="MedViet Data API", version="1.0.0")
anonymizer = MedVietAnonymizer()

RAW_CSV = "data/raw/patients_raw.csv"
# cccd & so_dien_thoai là định danh — đọc dạng str để giữ số 0 đầu
ID_DTYPES = {"cccd": str, "so_dien_thoai": str}


def load_raw(n: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(RAW_CSV, dtype=ID_DTYPES)
    return df.head(n) if n else df

# --- ENDPOINT 1 ---
@app.get("/api/patients/raw")
@require_permission(resource="patient_data", action="read")
async def get_raw_patients(
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Trả về raw patient data (chỉ admin được phép).
    Load từ data/raw/patients_raw.csv
    Trả về 10 records đầu tiên dưới dạng JSON.
    """
    df = load_raw(10)
    return {
        "user": current_user["username"],
        "count": len(df),
        "data": df.to_dict(orient="records"),
    }

# --- ENDPOINT 2 ---
@app.get("/api/patients/anonymized")
@require_permission(resource="training_data", action="read")
async def get_anonymized_patients(
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Trả về anonymized data (ml_engineer và admin được phép).
    Load raw data → anonymize → trả về JSON.
    """
    df = load_raw(10)
    df_anon = anonymizer.anonymize_dataframe(df)
    return {
        "user": current_user["username"],
        "count": len(df_anon),
        "data": df_anon.to_dict(orient="records"),
    }

# --- ENDPOINT 3 ---
@app.get("/api/metrics/aggregated")
@require_permission(resource="aggregated_metrics", action="read")
async def get_aggregated_metrics(
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Trả về aggregated metrics (data_analyst, ml_engineer, admin).
    Ví dụ: số bệnh nhân theo từng loại bệnh (không có PII).
    """
    df = load_raw()
    by_condition = df["benh"].value_counts().to_dict()
    return {
        "user": current_user["username"],
        "total_patients": len(df),
        "by_condition": by_condition,
        "avg_ket_qua_xet_nghiem": round(float(df["ket_qua_xet_nghiem"].mean()), 2),
    }

# --- ENDPOINT 4 ---
@app.delete("/api/patients/{patient_id}")
@require_permission(resource="patient_data", action="delete")
async def delete_patient(
    patient_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    TODO: Chỉ admin được xóa. Các role khác nhận 403.
    """
    return {
        "status": "deleted",
        "patient_id": patient_id,
        "by": current_user["username"],
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedViet Data API"}
