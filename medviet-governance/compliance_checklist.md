# NĐ13/2023 Compliance Checklist — MedViet AI Platform

## A. Data Localization
- [ ] Tất cả patient data lưu trên servers đặt tại Việt Nam
- [ ] Backup cũng phải ở trong lãnh thổ VN
- [ ] Log việc transfer data ra ngoài nếu có

## B. Explicit Consent
- [ ] Thu thập consent trước khi dùng data cho AI training
- [ ] Có mechanism để user rút consent (Right to Erasure)
- [ ] Lưu consent record với timestamp

## C. Breach Notification (72h)
- [ ] Có incident response plan
- [ ] Alert tự động khi phát hiện breach
- [ ] Quy trình báo cáo đến cơ quan có thẩm quyền trong 72h

## D. DPO Appointment
- [x] Đã bổ nhiệm Data Protection Officer
- [x] DPO có thể liên hệ tại: dpo@medviet.vn (+84 28 1234 5678)

## E. Technical Controls (mapping từ requirements)
| NĐ13 Requirement | Technical Control | Status | Owner |
|-----------------|-------------------|--------|-------|
| Data minimization | PII anonymization pipeline (Presidio) | ✅ Done | AI Team |
| Access control | RBAC (Casbin) + ABAC (OPA) | ✅ Done | Platform Team |
| Encryption | AES-256-GCM envelope (KEK/DEK) at rest, TLS 1.3 in transit | ✅ Done | Infra Team |
| Audit logging | API access logs (FastAPI middleware) → ghi user/role/resource/action/timestamp, ship sang ELK, immutable WORM bucket 1 năm | ✅ Done | Platform Team |
| Breach detection | Prometheus + Grafana alert: bất thường tần suất truy cập PII, login fail spike, export khối lượng lớn → PagerDuty | ✅ Done | Security Team |

## F. Mô tả chi tiết các control vừa hoàn thành

### Audit logging
- FastAPI dependency/middleware ghi mỗi request: `username, role, resource, action, status_code, ts`.
- Log đẩy về ELK stack; lưu immutable (WORM) ≥ 12 tháng phục vụ điều tra breach.
- Truy vết đủ để dựng lại "ai truy cập hồ sơ bệnh nhân nào, khi nào".

### Breach detection
- Prometheus scrape metrics từ API (counter theo endpoint/role, latency, error rate).
- Grafana alert rules:
  - Số lần đọc raw PII vượt ngưỡng/giờ.
  - Tỷ lệ 401/403 tăng đột biến (dấu hiệu brute-force/dò token).
  - Export dữ liệu khối lượng bất thường.
- Alert → PagerDuty → kích hoạt incident response plan (mục C, báo cáo 72h).
