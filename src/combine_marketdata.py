import pandas as pd
from config import DATA_RAW_DIR

def process_market_data():
    print("⏳ Đang đọc dữ liệu từ các file CSV...")
    # 1. Load dữ liệu
    df_history = pd.read_csv(DATA_RAW_DIR / "market_data_history.csv")
    df_regime = pd.read_csv(DATA_RAW_DIR / "simulation_market_regimes.csv")

    # 2. Ép kiểu cột Date sang datetime để lọc năm cho chuẩn
    df_history['Date'] = pd.to_datetime(df_history['Date'])
    df_regime['Date'] = pd.to_datetime(df_regime['Date'])

    # 3. Cắt dữ liệu, chỉ lấy năm 2025
    print("✂️ Đang lọc dữ liệu năm 2025...")
    df_history_2025 = df_history[df_history['Date'].dt.year == 2025].copy()
    df_regime_2025 = df_regime[df_regime['Date'].dt.year == 2025].copy()

    # 4. Gộp Market_Regime vào History
    # Chỉ giữ lại cột khóa (Date, Ticker) và cột cần gộp (Market_Regime) để tránh bị nhân đôi cột
    columns_to_merge = ['Date', 'Ticker', 'Market_Regime']
    
    print("🔄 Đang gộp Market_Regime vào dữ liệu chính...")
    df_final = pd.merge(
        df_history_2025, 
        df_regime_2025[columns_to_merge], 
        on=['Date', 'Ticker'], 
        how='inner' # Dùng inner join để đảm bảo dữ liệu khớp hoàn toàn ở cả 2 bảng
    )

    # 5. Đổi tên cột cho khớp với Schema Database mới của bạn luôn!
    # Đoạn này rất quan trọng để khi df.to_sql() không bị báo lỗi thiếu cột
    rename_mapping = {
        'Date': 'TradeDate',
        'Close': 'ClosePrice',
        'Percent_Change': 'DailyReturn' # Tùy vào file cũ của bạn tên là Percent_Change hay DailyReturn
    }
    df_final = df_final.rename(columns=rename_mapping)

    # 6. Xuất ra file Final
    output_filename = 'final_market_data_2025.csv'
    df_final.to_csv(output_filename, index=False)
    
    print(f"✅ Xong! Đã lưu thành công {len(df_final)} dòng dữ liệu vào file '{output_filename}'")
    
    # Hiển thị vài dòng để kiểm tra nhanh
    print("\nPreview 3 dòng đầu tiên:")
    print(df_final[['TradeDate', 'Ticker', 'ClosePrice', 'Market_Regime']].head(3))

if __name__ == "__main__":
    process_market_data()