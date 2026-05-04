import pandas as pd
import mplfinance as mpf 
from sqlalchemy import create_engine, types # Thêm types để định nghĩa kiểu dữ liệu SQL
from dotenv import load_dotenv
import os
import sys
# --- 0. FIX IMPORT (Thêm đoạn này để tìm thấy config.py) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if current_dir not in sys.path:
    sys.path.append(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from config import DB_CONNECTION_STR,TICKER_LIST



# --- 1. LOAD DATA (GIỮ NGUYÊN) ---
load_dotenv()
engine = create_engine(DB_CONNECTION_STR)

def get_simulation_data(ticker='VIC', start_date='2025-01-01', end_date='2025-12-31'):
    print(f"🔌 Đang kéo data {ticker}...")
    query = f"""
    SELECT Date, Open, High, Low, Close, Volume, 
           MA_20, RSI_14, MA_Volume_30
    FROM Market_Data 
    WHERE Ticker = '{ticker}' 
      AND Date >= '{start_date}' 
      AND Date <= '{end_date}'
    ORDER BY Date ASC
    """
    try:
        df = pd.read_sql(query, con=engine)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        print(f"❌ Lỗi SQL: {e}")
        return pd.DataFrame()

# --- 2. XỬ LÝ LOGIC (GIỮ NGUYÊN) ---
def process_market_regime(df):
    # 1. TÍNH TOÁN DỮ LIỆU
    df['Percent_Change'] = df['Close'].pct_change() * 100
    
    df['Future_Close_5D'] = df['Close'].shift(-5)
    df['Future_Return'] = ((df['Future_Close_5D'] - df['Close']) / df['Close']) * 100
    
    df['MA_Vol_20'] = df['Volume'].rolling(window=20).mean()
    df['Vol_Ratio'] = df['Volume'] / df['MA_Vol_20']

    # Fill NaN
    df['Percent_Change'] = df['Percent_Change'].fillna(0)
    df['Future_Return'] = df['Future_Return'].fillna(0)
    df['Vol_Ratio'] = df['Vol_Ratio'].fillna(1.0)

    # 2. PHÂN LOẠI
    def classify(row):
        pct_now = row['Percent_Change'] 
        f_ret = row['Future_Return']    
        
        # LỚP 1: HÀNH ĐỘNG MẠNH
        if pct_now > 2.0: return "EXPLOSION"
        if pct_now < -2.0: return "PANIC"

        # LỚP 2: VÙNG CHUẨN BỊ (God Mode)
        if f_ret > 3.0: return "SIDEWAY_ACCUMULATION"
        if f_ret < -3.0: return "SIDEWAY_DISTRIBUTION"
            
        return "SIDEWAY_NOISE"

    df['Market_Regime'] = df.apply(classify, axis=1)
    return df

# --- 3. VẼ NẾN (GIỮ NGUYÊN) ---
def visualize_candles(df_full, ticker, start_view=None, end_view=None):
    df_plot = df_full.set_index('Date').copy()
    
    if start_view and end_view:
        df_plot = df_plot.loc[start_view:end_view]
        print(f"🔍 Đang soi chart từ {start_view} đến {end_view}")
    else:
        print(f"🔍 Đang soi toàn bộ chart")

    if df_plot.empty:
        print("⚠️ Không có dữ liệu để vẽ!")
        return

    colors = {
        'EXPLOSION': 'purple', 'PANIC': 'red',                    
        'SIDEWAY_ACCUMULATION': 'green', 'SIDEWAY_DISTRIBUTION': 'orange',  
        'SIDEWAY_NOISE': 'white'           
    }

    mc = mpf.make_marketcolors(up='green', down='red', inherit=True)
    s  = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=True)

    fig, axlist = mpf.plot(df_plot, type='candle', style=s, volume=True, 
                           title=f'{ticker} Market Regimes',
                           ylabel='Price', ylabel_lower='Volume',
                           figsize=(14, 8), returnfig=True)
    
    ax_main = axlist[0] 
    dates = df_plot.index
    for i in range(len(dates) - 1):
        regime = df_plot.iloc[i]['Market_Regime']
        color = colors.get(regime, 'white')
        if regime != 'SIDEWAY_NOISE':
            ax_main.axvspan(i, i+1, facecolor=color, alpha=0.2)
    mpf.show()

# --- [MỚI] 4. LƯU VÀO DATABASE ---
def save_regimes_to_db(df, ticker, mode='append'):
    """
    Tạo bảng 'Simulation_Market_Regimes' và lưu dữ liệu.
    Dùng if_exists='replace' để tự động tạo lại bảng mới mỗi khi chạy.
    """
    # 1. Chuẩn bị data gọn nhẹ để lưu
    # Chỉ lấy các cột cần thiết cho Simulation
    cols_to_save = ['Date', 'Ticker', 'Close', 'Future_Return', 'Market_Regime']
    
    df_save = df.copy()
    
    # Thêm cột Ticker vì trong df lấy về từ get_simulation_data chưa có
    if 'Ticker' not in df_save.columns:
        df_save['Ticker'] = ticker
        
    # Chỉ giữ lại đúng các cột cần thiết
    df_save = df_save[cols_to_save]
    
    print(f"💾 [{ticker}] Đang lưu {len(df_save)} dòng vào DB (mode={mode})...")    
    try:
        # Lệnh thần thánh: Tự tạo bảng, tự map kiểu dữ liệu
        df_save.to_sql(
            'Simulation_Market_Regimes', 
            con=engine, 
            if_exists=mode, # Quan trọng: Xóa bảng cũ, tạo bảng mới
            index=False,
            dtype={
                'Date': types.DateTime(),
                'Ticker': types.String(10),
                'Market_Regime': types.String(50)
            }
        )
        print("✅ Đã lưu thành công vào SQL Server!")
    except Exception as e:
        print(f"❌ Lỗi khi lưu mã {ticker}: {e}")

# --- CHẠY CHƯƠNG TRÌNH ---
if __name__ == "__main__":
    print(f"🚀 Bắt đầu phân tích trạng thái cho {len(TICKER_LIST)} mã cổ phiếu...")
    # 1. Load Data
    for i, ticker in enumerate(TICKER_LIST):
        df = get_simulation_data(ticker=ticker, start_date='2025-01-01', end_date='2025-12-31')
    
        if not df.empty:
            # 2. Xử lý Logic
            print(f"⚙️ [{ticker}] Đang phân tích thị trường...")
            df_processed = process_market_regime(df)
        
            # 3. [QUAN TRỌNG] Lưu vào DB để dùng cho các bước sau
            write_mode = 'replace' if i == 0 else 'append'
            save_regimes_to_db(df_processed, ticker,mode=write_mode)
        
        # 4. Vẽ biểu đồ check lại (Optional)
        # visualize_candles(df_processed, ticker, start_view='2025-08-01', end_view='2025-12-31')
        
        else:
            print("Không có data.")