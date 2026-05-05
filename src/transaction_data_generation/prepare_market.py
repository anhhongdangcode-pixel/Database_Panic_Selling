import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from pathlib import Path

# --- SETUP IMPORT ---
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent  # Lùi 2 cấp: transaction_data_generation -> src

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from config import DB_CONNECTION_STR, DATA_RAW_DIR

def load_and_prepare_market_data():
    """
    Đọc CSV thị trường, tính Volatility, rename cột, và đẩy lên DB.
    """
    csv_path = DATA_RAW_DIR / "final_market_data_2025.csv"
    
    print(f"📂 Đang đọc dữ liệu thị trường từ: {csv_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"❌ Không tìm thấy file: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"✅ Đã đọc {len(df)} dòng từ CSV")
    
    # --- 1. TÍNH VOLATILITY (Rolling Std Dev) ---
    print("📊 Đang tính Volatility (rolling std 20 ngày, grouped by Ticker)...")
    
    # Chuyển TradeDate thành datetime nếu chưa
    if 'TradeDate' in df.columns:
        df['TradeDate'] = pd.to_datetime(df['TradeDate'])
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.rename(columns={'Date': 'TradeDate'}, inplace=True)
    
    # Sắp xếp theo Ticker và TradeDate
    df = df.sort_values(['Ticker', 'TradeDate']).reset_index(drop=True)
    
    # Tính rolling volatility per Ticker
    # Nếu Pct_Change chưa có thì tạo từ ClosePrice
    if 'Pct_Change' not in df.columns and 'ClosePrice' in df.columns:
        df['Pct_Change'] = df.groupby('Ticker')['ClosePrice'].pct_change()
    
    # Rolling std dev (20 ngày)
    df['Volatility'] = (
        df.groupby('Ticker')['Pct_Change']
        .transform(lambda x: x.rolling(window=20, min_periods=1).std())
        .round(4)
    )
    
    # Các dòng đầu tiên sẽ là NaN -> MySQL nhận NULL bình thường
    print(f"   -> Volatility: Min={df['Volatility'].min():.6f}, Max={df['Volatility'].max():.6f}")
    
    # --- 2. RENAME COLUMNS THEO SCHEMA ---
    print("🔄 Đang rename cột theo schema MarketData...")
    
    rename_map = {
        'Pct_Change': 'DailyReturn',
        'MA20': 'MA_20'
    }
    df = df.rename(columns=rename_map)
    
    # --- 3. GIỮ LẠI ĐÚNG CÁC CỘT SCHEMA ---
    schema_cols = [
        'TradeDate', 'Ticker', 'Open', 'High', 'Low', 'ClosePrice', 
        'Volume', 'DailyReturn', 'Volatility', 'MA_Volume_30', 'RSI_14', 'MA_20', 
        'Market_Regime'
    ]
    
    # Lọc chỉ cột có trong DataFrame
    available_cols = [col for col in schema_cols if col in df.columns]
    df = df[available_cols]
    
    # [QUAN TRỌNG] Loại bỏ dòng trùng lặp (TradeDate, Ticker)
    # Vì schema có UNIQUE INDEX idx_market_date_ticker, không cho phép 2 dòng cùng date+ticker
    # CSV hiện tại có 3984 dòng bị lặp 3 lần -> keep='first' để giữ bản ghi đầu tiên
    df_before = len(df)
    df = df.drop_duplicates(subset=['TradeDate', 'Ticker'], keep='first')
    df_after = len(df)
    
    print(f"✅ Giữ lại {len(available_cols)} cột")
    print(f"   Dòng: {df_before} → {df_after} (xóa {df_before - df_after} trùng lặp)")
    
    # --- 4. ĐẨY LÊN DB ---
    print("\n💾 Đang kết nối cơ sở dữ liệu...")
    
    try:
        engine = create_engine(DB_CONNECTION_STR)
        
        # Bước 1: Xóa dữ liệu cũ
        print("🧹 [DB] Đang xóa dữ liệu cũ từ MarketData...")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM MarketData"))
        
        # Bước 2: Đẩy dữ liệu mới (để pandas tự quản lý transaction)
        print(f"🚀 [DB] Đang đẩy {len(df)} dòng vào bảng MarketData (chunksize=500)...")
        df.to_sql('MarketData', con=engine, if_exists='append', index=False, chunksize=500)
            
        print(f"✅ [DB] Đã đẩy thành công {len(df)} dòng vào bảng MarketData!")
        
    except Exception as e:
        print(f"❌ [DB] Lỗi khi đẩy dữ liệu: {e}")
        raise

if __name__ == "__main__":
    load_and_prepare_market_data()