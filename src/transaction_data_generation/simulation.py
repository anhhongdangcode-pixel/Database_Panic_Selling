import sys
import os
import pandas as pd
import random
import uuid
from tqdm import tqdm
from sqlalchemy import create_engine, text
from datetime import datetime

# --- SETUP IMPORT ---
from pathlib import Path
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent # Lùi 2 cấp: transaction_data_generation -> src

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# [CẬP NHẬT] Import thêm SEED_VALUE
from config import DB_CONNECTION_STR, DATA_RAW_DIR, SEED_VALUE
from investor import InvestorAgent

# --- [CẬP NHẬT] THIẾT LẬP SEED (QUAN TRỌNG) ---
random.seed(SEED_VALUE)
print(f"🎲 Random Seed đã được cố định: {SEED_VALUE}")

# --- 1. CÁC HÀM HỖ TRỢ ---
def load_market_data(ticker, start_date, end_date, engine):
    print(f"📉 Đang tải dữ liệu thị trường cho {ticker}...")
    query = f"""
    SELECT Date, Ticker, Close, Market_Regime
    FROM Simulation_Market_Regimes
    WHERE Ticker = '{ticker}' 
      AND Date >= '{start_date}' 
      AND Date <= '{end_date}'
    ORDER BY Date ASC
    """
    df = pd.read_sql(query, con=engine)
    if df.empty:
        raise ValueError("❌ Không tìm thấy dữ liệu Market! Hãy chạy prepare_market.py trước.")
    df['Date'] = pd.to_datetime(df['Date'])
    return df

def load_investors(engine):
    print("👥 Đang đánh thức các nhà đầu tư...")
    query = "SELECT * FROM investors"
    df = pd.read_sql(query, con=engine)
    df = df.rename(columns={'Overconfidence': 'Risk_Appetite'})
    agents = []
    for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Initializing Agents"):
        agent = InvestorAgent(row)
        agents.append(agent)
    return agents

def calculate_execution_price(action, close_price, regime):
    slippage = 0.0
    if regime == 'EXPLOSION' and action == 'BUY':
        slippage = random.uniform(0.005, 0.02)
        return close_price * (1 + slippage)
    elif regime == 'PANIC' and action == 'SELL':
        slippage = random.uniform(0.01, 0.03)
        return close_price * (1 - slippage)
    return close_price 

def save_csv_clean(df, file_name):
    """
    [CẬP NHẬT] Hàm lưu CSV an toàn:
    - Kiểm tra xem file cũ có tồn tại không.
    - Nếu có -> Xóa bỏ hoàn toàn.
    - Sau đó mới lưu file mới.
    """
    file_path = DATA_RAW_DIR / file_name
    
    if os.path.exists(file_path):
        os.remove(file_path) # Xóa file cũ
        # print(f"   (Đã xóa file cũ: {file_name})")
        
    df.to_csv(file_path, index=False)
    print(f" -> CSV: Đã lưu mới tại {file_path}")

# --- 2. ENGINE MÔ PHỎNG CHÍNH ---
def run_simulation(ticker='VIC', start_date='2025-01-01', end_date='2025-12-31'):
    engine = create_engine(DB_CONNECTION_STR)
    agents = load_investors(engine)
    # A. Load Dữ liệu
    all_market_df = pd.read_sql("SELECT * FROM Simulation_Market_Regimes ORDER BY Date ASC", con=engine)
    all_dates = sorted(all_market_df['Date'].unique())

    all_transactions = []
    daily_portfolio_snapshots = []
    
    # Vòng lap tầng 1: Theo ngày
    for current_date in tqdm(all_dates, desc="Đang mô phỏng từng ngày"):
        # Lấy dữ liệu của tất cả các mã trong ngày hôm nay
        day_data = all_market_df[all_market_df['Date'] == current_date]
    
        # Tạo bảng giá nhanh để Snapshot cuối ngày: {'VIC': 45.0, 'FPT': 90.0, ...}
        today_prices = dict(zip(day_data['Ticker'], day_data['Close']))
        
        # vòng lạp tầng 2: theo mã cổ phiếu
        for agent in agents:
            #vòng lap tầng 3: theo nhà đầu tu
            for _, market_row in day_data.iterrows():
                ticker = market_row['Ticker']
                regime = market_row['Market_Regime']
                current_price = market_row['Close']
        
                market_info = {'Date': current_date, 'Close': current_price, 'Market_Regime': regime}
                trade_record = None                
                if agent.check_wake_up(ticker, market_info):
                    trade_record = agent.decide_action(ticker, market_info)
            
                if trade_record:
                    # Tính giá khớp lệnh (có trượt giá slippage)
                    exec_price = calculate_execution_price(trade_record['Action'], current_price, regime)
                
                    trade_record['Trans_ID'] = str(uuid.uuid4())[:8]
                    trade_record['Price'] = round(exec_price, 2)
                    # Ticker đã có trong trade_record trả về từ Agent
                    all_transactions.append(trade_record)

        # D. Snapshot cuối ngày
        for agent in agents:
            snapshot = agent.portfolio.get_snapshot(current_date, today_prices)
            daily_portfolio_snapshots.append(snapshot)

    # --- 3. LƯU KẾT QUẢ ---
    print("\n💾 Đang lưu kết quả...")
    
    # --- XỬ LÝ TRANSACTIONS ---
    if all_transactions:
        df_trans = pd.DataFrame(all_transactions)
        
        # [CẬP NHẬT] Tên bảng: transactions
        cols_trans_sql = ['Trans_ID', 'Investor_ID', 'Date', 'Ticker', 'Action', 'Price', 'Quantity', 'Return_Pct', 'Reason']
        df_trans_sql = df_trans[cols_trans_sql]
        
        # 1. Lưu CSV (Xóa cũ -> Lưu mới)
        save_csv_clean(df_trans, "simulation_transactions.csv")

        # 2. Lưu SQL (Safe Append)
        print(f" -> SQL: Đang đẩy {len(df_trans_sql)} dòng vào bảng 'transactions'...")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM transactions")) # [CẬP NHẬT] Tên bảng chuẩn
            df_trans_sql.to_sql('transactions', con=conn, if_exists='append', index=False)
            
    else:
        print("⚠️ Không có giao dịch nào được tạo ra!")

    # --- XỬ LÝ PORTFOLIO HISTORY ---
    if daily_portfolio_snapshots:
        df_port = pd.DataFrame(daily_portfolio_snapshots)
        
        # [CẬP NHẬT] Tên bảng: portfolio_history
        cols_port_sql = ['Date', 'Investor_ID', 'Total_Asset', 'Cash_Balance', 'Stock_Value']
        df_port_sql = df_port[cols_port_sql]

        # 1. Lưu CSV (Xóa cũ -> Lưu mới)
        save_csv_clean(df_port, "simulation_portfolio_history.csv")

        # 2. Lưu SQL (Safe Append)
        print(f" -> SQL: Đang đẩy lịch sử tài sản vào bảng 'portfolio_history'...")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM portfolio_history")) # [CẬP NHẬT] Tên bảng chuẩn
            df_port_sql.to_sql('portfolio_history', con=conn, if_exists='append', index=False)

    print("\n🎉 MÔ PHỎNG HOÀN TẤT!")

if __name__ == "__main__":
    run_simulation()