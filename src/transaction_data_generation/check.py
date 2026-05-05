# --- SETUP IMPORT ---
import sys
import os
import pandas as pd
import random
import uuid
from tqdm import tqdm
from sqlalchemy import create_engine, text
from datetime import datetime
from pathlib import Path
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent # Lùi 2 cấp: transaction_data_generation -> src

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# [CẬP NHẬT] Import thêm SEED_VALUE
from config import DB_CONNECTION_STR, DATA_RAW_DIR, SEED_VALUE
from investor import InvestorAgent


# In ra chuỗi kết nối để kiểm tra bằng mắt trước
print(f"Chuỗi kết nối trong config.py: {DB_CONNECTION_STR}")

try:
    # Tạo engine và kết nối thử
    engine = create_engine(DB_CONNECTION_STR)
    with engine.connect() as conn:
        # Lệnh SELECT DATABASE() sẽ trả về tên DB đang được active
        current_db = conn.execute(text("SELECT DATABASE();")).scalar()
        print(f"🔥 XÁC NHẬN: Python đang thao tác trên database: >>> {current_db} <<<")
        
        # Tiện tay đếm thử số bảng trong DB này luôn
        tables = conn.execute(text("SHOW TABLES;")).fetchall()
        print(f"📂 Database này hiện có {len(tables)} bảng: {[t[0] for t in tables]}")
        
except Exception as e:
    print(f"❌ Kết nối thất bại, lỗi: {e}")
    