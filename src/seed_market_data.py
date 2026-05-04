import sys
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from config import DATA_RAW_DIR, DB_CONNECTION_STR

load_dotenv() 

from config import DB_CONNECTION_STR, ROOT_DIR
engine = create_engine(DB_CONNECTION_STR)

def push_csv_to_mysql(csv_file_path):
    try:
        df = pd.read_csv(csv_file_path)
        
        # Ánh xạ tên cột khớp 100% với schema.sql
        df = df.rename(columns={
            'Time': 'Date',
            'MA20': 'MA_20',                # MA20 (indicator) -> MA_20 (SQL)
            'Pct_Change': 'Percent_Change'  # Pct_Change (indicator) -> Percent_Change (SQL)
        })

        # Chọn ĐỦ 10 cột theo Schema
        cols_to_keep = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume', 'MA_Volume_30', 'RSI_14', 'MA_20', 'Percent_Change']
        df_clean = df[[c for c in cols_to_keep if c in df.columns]].fillna(0)

        with engine.begin() as connection:
            # Xóa dữ liệu cũ để tránh lỗi trùng khóa chính (Primary Key)
            connection.execute(text("TRUNCATE TABLE Market_Data"))
            print("🚀 Đang bơm dữ liệu đầy đủ vào bảng Market_Data...")
            df_clean.to_sql('Market_Data', con=connection, if_exists='append', index=False, chunksize=1000)
            
        print(f"🎉 THÀNH CÔNG! Đã nạp {len(df_clean)} dòng.")
    except Exception as e:
        print(f"❌ LỖI: {e}")

if __name__ == "__main__":
    file_name = "market_data_history.csv" 
    file_path = DATA_RAW_DIR / file_name 
    
    if file_path.exists():
        push_csv_to_mysql(file_path)
    else:
        print(f"❌ Không tìm thấy file tại: {file_path}")