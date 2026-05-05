import sys
import pandas as pd
import random
import uuid
from faker import Faker
from sqlalchemy import create_engine, text
import os
from config import DB_CONNECTION_STR, DATA_RAW_DIR, SEED_VALUE

# --- SETUP ---
random.seed(SEED_VALUE)
Faker.seed(SEED_VALUE)
fake = Faker('vi_VN')
NUM_INVESTORS = 300
CSV_FILE_PATH = DATA_RAW_DIR / "investors_dummy_data.csv"

def generate_dummy_data(n_rows):
    """
    Hàm sinh dữ liệu SẠCH (Đã xóa vĩnh viễn Debug_Type)
    """
    data = []
    print(f"🔄 [GENERATE] Đang sinh mới {n_rows} investors (Seed={SEED_VALUE})...")
    
    for _ in range(n_rows):
        inv_id = str(uuid.uuid4())[:8]
        name = fake.name()
        dice = random.random()
        
        # Logic phân loại (Giữ nguyên)
        if dice < 0.30: 
            investor_type = 'FOMO'
            chasing = random.uniform(0.75, 0.99)
            loss_aversion = random.uniform(0.70, 0.95)
            risk_appetite = random.uniform(0.60, 0.90) 
            impatience = random.uniform(0.75, 1.0)
        elif dice < 0.80:
            investor_type = 'RATIONAL'
            chasing = random.uniform(0.01, 0.25)
            loss_aversion = random.uniform(0.1, 0.4)
            risk_appetite = random.uniform(0.10, 0.35)
            impatience = random.uniform(0.05, 0.3)
        else:
            investor_type = 'NOISE'
            chasing = random.uniform(0.3, 0.7)
            loss_aversion = random.uniform(0.3, 0.7)
            risk_appetite = random.uniform(0.3, 0.7)
            impatience = random.uniform(0.3, 0.7)

        initial_balance = random.randint(10, 5000) * 1_000_000 
        # Sinh ngày gia nhập ngẫu nhiên trong 2 năm gần nhất
        join_date = fake.date_between(start_date='-9y', end_date='today')

        row = {
            "InvestorID": inv_id,
            "InvestorName": name,
            "RiskProfile": investor_type,
            "JoinDate": join_date.isoformat(),
            "Chasing_Bias": round(chasing, 2),
            "Loss_Aversion": round(loss_aversion, 2),
            "Risk_Appetite": round(risk_appetite, 2),
            "Impatience": round(impatience, 2),
            "Initial_Balance": initial_balance
        }
        data.append(row)
    
    return pd.DataFrame(data)

def push_to_mysql(df):
    """
    Logic: Lọc bỏ cột rác -> Xóa bảng cũ -> Đổ bảng mới.
    """
    # 1. BỘ LỌC AN TOÀN: Nếu thấy Debug_Type thì vứt ngay
    if 'Debug_Type' in df.columns:
        print("🛠️ Đang loại bỏ cột thừa 'Debug_Type'...")
        df = df.drop(columns=['Debug_Type'])
        
    engine = create_engine(DB_CONNECTION_STR)
    
    try:
        with engine.begin() as conn:
            # 2. Xóa sạch dữ liệu cũ (Reset bảng)
            print("🧹 [DB] Đang dọn dẹp các bảng liên quan (Warnings -> BehaviorSignals -> Trades -> Portfolios -> Investors)...")
            conn.execute(text("DELETE FROM Warnings"))
            conn.execute(text("DELETE FROM BehaviorSignals"))
            conn.execute(text("DELETE FROM Trades"))
            conn.execute(text("DELETE FROM Portfolios"))
            conn.execute(text("DELETE FROM Investors"))

            # Đảm bảo tên cột khớp schema mới nếu CSV cũ chứa tên cũ
            df_to_db = df.copy()
            rename_map = {
                'Investor_ID': 'InvestorID',
                'Name': 'InvestorName',
                'Investor_Type': 'RiskProfile',
                'Date': 'JoinDate'
            }
            df_to_db = df_to_db.rename(columns=rename_map)

            # 3. Đổ dữ liệu vào (bảng 'Investors')
            print(f"🚀 [DB] Đang đẩy {len(df_to_db)} dòng vào bảng 'Investors'...")
            df_to_db.to_sql('Investors', con=conn, if_exists='append', index=False)
            
        print("✅ [DB] Đã đồng bộ thành công! (Database == CSV)")
        
    except Exception as e:
        print("❌ [DB] Lỗi MySQL:", e)     

def main():
    # 1. KIỂM TRA FILE CSV
    if os.path.exists(CSV_FILE_PATH):
        print(f"⚠️ [INFO] Tìm thấy file CSV cũ tại: {CSV_FILE_PATH}")
        print("   -> Đang đọc dữ liệu từ file này...")
        df = pd.read_csv(CSV_FILE_PATH)
        
    else:
        print(f"🆕 [INFO] Chưa thấy CSV. Bắt đầu sinh dữ liệu mới...")
        df = generate_dummy_data(NUM_INVESTORS)
        
        # Lưu file CSV sạch (không có Debug_Type)
        os.makedirs(DATA_RAW_DIR, exist_ok=True)
        df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8-sig')
        print(f"💾 [FILE] Đã tạo file: {CSV_FILE_PATH}")
    
    # 2. ĐỒNG BỘ DB
    push_to_mysql(df)

if __name__ == "__main__":
    main()