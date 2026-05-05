import sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
from vnstock import Vnstock
import argparse
import os
from datetime import datetime
from indicator import basic_feature_engineering
from config import DATA_RAW_DIR,TICKER_LIST

print("Start loading VIC stock market data (src: VCI)...")

# ------------------ Parse command line arguments ------------------

parser = argparse.ArgumentParser()
parser.add_argument('--output_dir', type=str, default=str(DATA_RAW_DIR),
                    help='Mặc định sẽ lưu vào thư mục data/raw của dự án')
parser.add_argument('--filename', type=str, default="market_data_history.csv",
                    help='Tên file lưu trữ dữ liệu (mặc định: market_data_history.csv)')
args = parser.parse_args()

# Create output directory if it doesn't exist
os.makedirs(args.output_dir, exist_ok=True)

# ------------------ List of stock symbols ------------------
symbols = TICKER_LIST if 'TICKER_LIST' in globals() else ['VIC', 'VHM', 'HPG', 'FPT', 'VCB', 'SSI', 'VPB', 'BCM', 'MSN']

final_data_list = []

for symbol in symbols:
    print(f"🔄 Đang xử lý mã: {symbol}...")
    try:
        stock = Vnstock().stock(symbol=symbol, source='TCBS')
        df = stock.quote.history(
            start='2018-01-01',
            end='2025-12-31',
            interval='1D'
        )
    
        if df is not None and not df.empty:
            df = df.rename(columns={
            'time': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'ticker': 'Ticker'
            })
            df['Ticker'] = symbol
            df['Date'] = pd.to_datetime(df['Date'])
            # Tính toán các chỉ số (sinh ra Pct_Change, MA20, RSI_14)
            df = basic_feature_engineering(df)
            final_data_list.append(df)  
            print(f" ✅ Thành công: {len(df)} dòng cho {symbol}")
        else:
            print(f"No data for {symbol}")

    except Exception as e:  
        print(f"Error loading {symbol}: {e}")
# ------------------ Save file ------------------
if final_data_list:
    full_df = pd.concat(final_data_list, ignore_index=True)
    # Determine output filename
    output_path = os.path.join(args.output_dir, args.filename)
    full_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\nSaved success: {output_path}")
    print(f"Size: {len(full_df):,} rows")
    print("Main columns: time, open, high, low, close, volume, ticker")
else:
    print("No data loaded. Check connection or stock symbols.")
