import sys
import os
from pathlib import Path
from dotenv import load_dotenv

try:
    # Chỉ chạy reconfigure nếu sys.stdout hỗ trợ (ví dụ terminal thật)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# =============================================
# 1. Xác định đường dẫn dự án (rất quan trọng)
# =============================================
FILE_DIR = Path(__file__).resolve().parent          # → thư mục src/
ROOT_DIR = FILE_DIR.parent                          # → thư mục gốc FOMO-DETECTION/

# =============================================
# 2. Load file .env từ thư mục gốc dự án
# =============================================
env_path = ROOT_DIR / ".env"
load_dotenv(env_path, override=True)

# Debug để biết .env có load được không
print("=== CONFIG.PY DEBUG ===")
print(f"Project root:          {ROOT_DIR}")
print(f".env file path:        {env_path}")
print(f".env tồn tại?          {env_path.exists()}")
print(f"DB_HOST từ env:        {os.getenv('DB_HOST')}")
print("=======================\n")

# =============================================
# 3. Các biến database - có fallback an toàn
# =============================================
DB_USER     = os.getenv("DB_USER")     or "root"
DB_PASSWORD = os.getenv("DB_PASSWORD") or ""
DB_HOST     = os.getenv("DB_HOST")     or "127.0.0.1"
DB_PORT     = os.getenv("DB_PORT")     or "3306"
DB_NAME     = os.getenv("DB_NAME")     or "panic_selling_projects"

# Xây dựng connection string an toàn
user_part = DB_USER
pass_part = f":{DB_PASSWORD}" if DB_PASSWORD else ""

DB_CONNECTION_STR = (
    f"mysql+pymysql://{user_part}{pass_part}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)
safe_conn = DB_CONNECTION_STR.replace(DB_PASSWORD, "****" if DB_PASSWORD else "")
print(f"Connection string (ẩn pass): {safe_conn}")

# =============================================
# 4. Đường dẫn dữ liệu - tự động tạo thư mục
# =============================================
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DATA_DIR = ROOT_DIR / "data" / "processed"

# Tự động tạo thư mục nếu chưa có
for d in [DATA_RAW_DIR, PROCESSED_DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)
    print(f"Thư mục đã sẵn sàng: {d}")

# =============================================
# 5. Các hằng số khác (đồng bộ với investor_data_generation)
# =============================================
SEED_VALUE = 2026
TICKER_LIST = ['VIC', 'VHM', 'HPG', 'FPT', 'VCB', 'SSI', 'VPB', 'BCM', 'MSN']