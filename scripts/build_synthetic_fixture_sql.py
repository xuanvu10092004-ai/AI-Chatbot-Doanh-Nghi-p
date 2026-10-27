"""Build an isolated, synthetic SQL fixture without copying live customer data."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ai_training" / "fixtures" / "honda_chatbot_test.sql"
BASE = ROOT / "data" / "schema" / "honda_chatbot_rbac.sql"
EXTENSIONS = ROOT / "data" / "schema" / "extensions"

PROFILE_DDL = """
CREATE TABLE customer_profiles (
  user_id INT PRIMARY KEY,
  customer_code VARCHAR(30) UNIQUE NOT NULL,
  gender VARCHAR(20), birth_date DATE, province VARCHAR(80), district VARCHAR(80),
  address VARCHAR(255), occupation VARCHAR(100), lead_source VARCHAR(50),
  interested_product_id INT NULL, payment_preference VARCHAR(30),
  registered_at DATE, status VARCHAR(40) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (interested_product_id) REFERENCES products(id)
);
INSERT INTO customer_profiles
(user_id, customer_code, gender, birth_date, province, district, address, occupation,
 lead_source, interested_product_id, payment_preference, registered_at, status) VALUES
(8, 'TEST-KH-001', 'Nữ', '1990-01-01', 'Khánh Hòa', 'Nha Trang', 'Địa chỉ synthetic 1', 'Nhân viên', 'Website', 8, 'Trả thẳng', '2026-01-01', 'Đã mua'),
(9, 'TEST-KH-002', 'Nam', '1992-02-02', 'Khánh Hòa', 'Cam Ranh', 'Địa chỉ synthetic 2', 'Kỹ thuật', 'Hotline', 6, 'Trả góp', '2026-01-02', 'Tiềm năng');
""".strip()


def transform(sql: str) -> str:
    sql = sql.replace("DROP DATABASE IF EXISTS honda_chatbot;", "DROP DATABASE IF EXISTS honda_chatbot_test;")
    sql = sql.replace("CREATE DATABASE honda_chatbot ", "CREATE DATABASE honda_chatbot_test ")
    sql = sql.replace("USE honda_chatbot;", "USE honda_chatbot_test;")
    return sql


def main() -> None:
    parts = [
        "-- Synthetic fixture only. No live import/PII is included.",
        transform(BASE.read_text(encoding="utf-8")),
        PROFILE_DDL,
    ]
    for name in ("02_ai_views.sql", "04_indexes.sql", "06_auth_dynamic_rbac.sql"):
        text = (EXTENSIONS / name).read_text(encoding="utf-8")
        parts.append(transform(text))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote synthetic fixture: {OUT}")


if __name__ == "__main__":
    main()
