"""
engineering_feature.py
-----------------------
Tính 3 BehaviorSignals từ Trades + Portfolios đã có trong DB:
  - DrawdownLevel    : max loss từ đỉnh NAV trong 30 ngày gần nhất
  - SellSpike        : tỷ lệ lệnh SELL có Reason chứa PANIC/DISTRIBUTION / tổng SELL trong 30 ngày
  - LossSensitivity  : tỷ lệ lệnh SELL có Return_Pct < 0 / tổng SELL trong 30 ngày

PanicScore = 0.4 * DrawdownLevel + 0.4 * SellSpike + 0.2 * LossSensitivity

Sau đó INSERT vào bảng BehaviorSignals (trigger tự bắn vào Warnings).

Cách chạy:
    cd src
    python engineering_feature.py
"""

import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from tqdm import tqdm

# --- Fix import path ---
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
if FILE_DIR not in sys.path:
    sys.path.insert(0, FILE_DIR)

from config import DB_CONNECTION_STR, DATA_RAW_DIR

# ============================================================
# CONFIG
# ============================================================
WINDOW_DAYS     = 30     # Cửa sổ tính signal (30 ngày)
PANIC_THRESHOLD = 0.65   # Ngưỡng trigger Warning
WEIGHTS = {
    'drawdown':        0.4,
    'sell_spike':      0.4,
    'loss_sensitivity': 0.2,
}

# ============================================================
# LOAD DATA
# ============================================================
def load_data(engine):
    print("📥 Đang tải dữ liệu từ DB...")

    trades_df = pd.read_sql("""
        SELECT InvestorID, TradeDate, TradeType, Return_Pct, Reason
        FROM Trades
    """, engine)

    portfolios_df = pd.read_sql("""
        SELECT InvestorID, TradeDate, NAV
        FROM Portfolios
    """, engine)

    investors_df = pd.read_sql("""
        SELECT InvestorID FROM Investors
    """, engine)

    # Chuẩn hóa kiểu ngày
    trades_df['TradeDate']     = pd.to_datetime(trades_df['TradeDate'])
    portfolios_df['TradeDate'] = pd.to_datetime(portfolios_df['TradeDate'])

    print(f"  ✅ Trades: {len(trades_df):,} rows")
    print(f"  ✅ Portfolios: {len(portfolios_df):,} rows")
    print(f"  ✅ Investors: {len(investors_df):,} rows")

    return investors_df, trades_df, portfolios_df


# ============================================================
# TÍNH 3 SIGNALS CHO 1 INVESTOR TẠI 1 NGÀY
# ============================================================
def compute_signals_for_investor(investor_id, obs_date, trades_df, portfolios_df):
    """
    Trả về dict {DrawdownLevel, SellSpike, LossSensitivity, PanicScore}
    hoặc None nếu không đủ dữ liệu.
    """
    start_date = obs_date - pd.Timedelta(days=WINDOW_DAYS)

    # --- Lọc dữ liệu trong cửa sổ ---
    inv_port = portfolios_df[
        (portfolios_df['InvestorID'] == investor_id) &
        (portfolios_df['TradeDate'] >= start_date) &
        (portfolios_df['TradeDate'] <= obs_date)
    ].sort_values('TradeDate')

    inv_trades = trades_df[
        (trades_df['InvestorID'] == investor_id) &
        (trades_df['TradeDate'] >= start_date) &
        (trades_df['TradeDate'] <= obs_date)
    ]

    # Cần ít nhất 5 ngày portfolio và có ít nhất 1 lệnh
    if len(inv_port) < 5 or len(inv_trades) == 0:
        return None

    # -------------------------------------------------------
    # SIGNAL 1: DrawdownLevel
    # (peak NAV - NAV cuối cửa sổ) / peak NAV
    # Đo mức độ thua lỗ so với đỉnh trong 30 ngày
    # -------------------------------------------------------
    peak_nav  = inv_port['NAV'].max()
    final_nav = inv_port['NAV'].iloc[-1]

    if peak_nav <= 0:
        drawdown = 0.0
    else:
        drawdown = max(0.0, (peak_nav - final_nav) / peak_nav)

    # -------------------------------------------------------
    # SIGNAL 2: SellSpike
    # Tỷ lệ SELL "hoảng loạn" (Reason có PANIC hoặc DISTRIBUTION)
    # trên tổng số lệnh SELL trong cửa sổ
    # -------------------------------------------------------
    sell_trades = inv_trades[inv_trades['TradeType'] == 'SELL']

    if len(sell_trades) == 0:
        sell_spike = 0.0
    else:
        panic_sells = sell_trades['Reason'].str.contains(
            'PANIC|DISTRIBUTION', case=False, na=False
        ).sum()
        sell_spike = panic_sells / len(sell_trades)

    # -------------------------------------------------------
    # SIGNAL 3: LossSensitivity
    # Tỷ lệ lệnh SELL có Return_Pct < 0 (bán lỗ / cut loss)
    # trên tổng SELL trong cửa sổ
    # Investor FOMO hay bán lỗ vì hoảng loạn
    # -------------------------------------------------------
    if len(sell_trades) == 0:
        loss_sensitivity = 0.0
    else:
        loss_sells = (sell_trades['Return_Pct'] < 0).sum()
        loss_sensitivity = loss_sells / len(sell_trades)

    # -------------------------------------------------------
    # PANIC SCORE (weighted sum, clamp to [0, 1])
    # -------------------------------------------------------
    panic_score = (
        WEIGHTS['drawdown']         * drawdown +
        WEIGHTS['sell_spike']       * sell_spike +
        WEIGHTS['loss_sensitivity'] * loss_sensitivity
    )
    panic_score = float(np.clip(panic_score, 0.0, 1.0))

    return {
        'DrawdownLevel':    round(drawdown, 4),
        'SellSpike':        round(sell_spike, 4),
        'LossSensitivity':  round(loss_sensitivity, 4),
        'PanicScore':       round(panic_score, 4),
    }


# ============================================================
# BUILD TOÀN BỘ DATASET & PUSH VÀO DB
# ============================================================
def build_and_push_behavior_signals(engine):
    investors_df, trades_df, portfolios_df = load_data(engine)

    # Chọn ngày quan sát: ngày cuối cùng trong portfolio history
    # (hoặc có thể chạy theo từng tháng nếu muốn)
    last_date = portfolios_df['TradeDate'].max()
    obs_date  = last_date
    print(f"\n📅 Ngày quan sát: {obs_date.date()}")

    # --- Tính signals cho từng investor ---
    records = []
    print("\n⚙️  Đang tính BehaviorSignals cho từng investor...")

    for _, row in tqdm(investors_df.iterrows(), total=len(investors_df)):
        inv_id = row['InvestorID']
        signals = compute_signals_for_investor(
            inv_id, obs_date, trades_df, portfolios_df
        )
        if signals is None:
            continue

        records.append({
            'InvestorID':      inv_id,
            'ObservationDate': obs_date.date(),
            **signals
        })

    if not records:
        print("⚠️  Không có dữ liệu đủ để tính signals. Kiểm tra lại DB.")
        return

    df_signals = pd.DataFrame(records)

    print(f"\n📊 Kết quả tính toán ({len(df_signals)} investors):")
    print(df_signals[['InvestorID', 'DrawdownLevel', 'SellSpike',
                       'LossSensitivity', 'PanicScore']].describe().round(4))

    # --- Thống kê PanicLevel ---
    df_signals['PanicLevel'] = df_signals['PanicScore'].apply(
        lambda s: 'High' if s >= 0.80 else ('Medium' if s >= 0.65 else 'Low')
    )
    print("\n📈 Phân phối PanicLevel:")
    print(df_signals['PanicLevel'].value_counts())

    # --- Lưu CSV để backup ---
    csv_path = DATA_RAW_DIR / 'behavior_signals.csv'
    df_signals.to_csv(csv_path, index=False)
    print(f"\n💾 Đã lưu CSV: {csv_path}")

    # --- Push vào MySQL ---
    print("\n🚀 Đang đẩy vào bảng BehaviorSignals (trigger sẽ tự fill Warnings)...")
    cols_to_db = [
        'InvestorID', 'ObservationDate',
        'DrawdownLevel', 'SellSpike', 'LossSensitivity', 'PanicScore'
    ]
    df_to_db = df_signals[cols_to_db]

    with engine.begin() as conn:
        # Xóa data cũ của ngày này để tránh duplicate
        conn.execute(
            text("DELETE FROM BehaviorSignals WHERE ObservationDate = :d"),
            {"d": str(obs_date.date())}
        )
        df_to_db.to_sql(
            'BehaviorSignals',
            con=conn,
            if_exists='append',
            index=False,
            chunksize=500
        )

    # --- Kiểm tra Warnings được tạo tự động ---
    with engine.connect() as conn:
        warning_count = conn.execute(
            text("SELECT COUNT(*) FROM Warnings WHERE WarningDate = :d"),
            {"d": str(obs_date.date())}
        ).scalar()

    print(f"\n✅ Đã push {len(df_to_db)} BehaviorSignals")
    print(f"🔔 Trigger đã tạo {warning_count} Warnings tự động")
    print("\n🎉 HOÀN TẤT!")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    engine = create_engine(DB_CONNECTION_STR)
    build_and_push_behavior_signals(engine)
