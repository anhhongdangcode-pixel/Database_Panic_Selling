"""
engineering_feature.py
-----------------------
Tính 3 BehaviorSignals từ Trades + Portfolios đã có trong DB:
  - DrawdownLevel    : max loss từ đỉnh NAV trong 30 ngày gần nhất
  - SellSpike        : tỷ lệ lệnh SELL có Reason chứa PANIC/DISTRIBUTION / tổng SELL trong 30 ngày
  - LossSensitivity  : tỷ lệ lệnh SELL có Return_Pct < 0 / tổng SELL trong 30 ngày

PanicScore = 0.4 * DrawdownLevel + 0.4 * SellSpike + 0.2 * LossSensitivity

Sau đó backfill vào bảng BehaviorSignals theo từng ngày (trigger tự bắn vào Warnings).

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
MIN_PORTFOLIO_ROWS = 2    # Chỉ cần tối thiểu 2 snapshot để tính drawdown
PANIC_THRESHOLD = 0.4   # Ngưỡng trigger Warning
WEIGHTS = {
    'drawdown':        0.4,
    'sell_spike':      0.4,
    'loss_sensitivity': 0.2,
}


def fn_Calculate_Panic_Score(df_signals):
    """Tính PanicScore bằng vector hóa trên DataFrame."""
    panic_score = (
        WEIGHTS['drawdown'] * df_signals['DrawdownLevel'] +
        WEIGHTS['sell_spike'] * df_signals['SellSpike'] +
        WEIGHTS['loss_sensitivity'] * df_signals['LossSensitivity']
    )
    return np.clip(panic_score, 0.0, 1.0)

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

    # Nếu không có đủ portfolio snapshot thì không tính được drawdown
    if len(inv_port) < MIN_PORTFOLIO_ROWS:
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
        raw_drawdown = max(0.0, (peak_nav - final_nav) / peak_nav)
        # Bơm hệ số x5 để scale điểm số lên sát thực tế tâm lý hoảng loạn
        drawdown = float(np.clip(raw_drawdown * 5.0, 0.0, 1.0))
    # -------------------------------------------------------
    # SIGNAL 2: SellSpike
    # Tỷ lệ SELL "hoảng loạn" (Reason có PANIC hoặc DISTRIBUTION)
    # trên tổng số lệnh SELL trong cửa sổ
    # -------------------------------------------------------
    sell_trades = inv_trades[inv_trades['TradeType'] == 'SELL']

    if len(sell_trades) == 0:
        sell_spike = 0.0
        loss_sensitivity = 0.0
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
    _, trades_df, portfolios_df = load_data(engine)

    trading_dates = pd.Index(portfolios_df['TradeDate'].dropna().sort_values().unique())
    daily_frames = []

    print("\n⚙️  Đang backfill BehaviorSignals theo từng ngày...")
    print(f"   -> Tổng số ngày giao dịch: {len(trading_dates):,}")

    for current_date in tqdm(trading_dates, total=len(trading_dates)):
        window_start = current_date - pd.Timedelta(days=WINDOW_DAYS)

        window_portfolios = portfolios_df[
            (portfolios_df['TradeDate'] >= window_start) &
            (portfolios_df['TradeDate'] <= current_date)
        ].sort_values(['InvestorID', 'TradeDate'])

        if window_portfolios.empty:
            continue

        drawdown_df = (
            window_portfolios
            .groupby('InvestorID', as_index=False)
            .agg(
                PeakNAV=('NAV', 'max'),
                FinalNAV=('NAV', 'last'),
                PortfolioRows=('NAV', 'size')
            )
        )
        drawdown_df = drawdown_df[drawdown_df['PortfolioRows'] >= MIN_PORTFOLIO_ROWS].copy()

        if drawdown_df.empty:
            continue

        raw_drawdown = (drawdown_df['PeakNAV'] - drawdown_df['FinalNAV']) / drawdown_df['PeakNAV']
        raw_drawdown = raw_drawdown.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        drawdown_df['DrawdownLevel'] = np.clip(raw_drawdown * 5.0, 0.0, 1.0)

        window_trades = trades_df[
            (trades_df['TradeDate'] >= window_start) &
            (trades_df['TradeDate'] <= current_date)
        ].copy()

        if window_trades.empty:
            trade_df = pd.DataFrame(columns=['InvestorID', 'TotalSell', 'PanicSell', 'LossSell'])
        else:
            sell_trades = window_trades[window_trades['TradeType'] == 'SELL'].copy()

            if sell_trades.empty:
                trade_df = pd.DataFrame(columns=['InvestorID', 'TotalSell', 'PanicSell', 'LossSell'])
            else:
                sell_trades['IsPanicSell'] = sell_trades['Reason'].str.contains(
                    'PANIC|DISTRIBUTION', case=False, na=False
                ).astype(np.int8)
                sell_trades['IsLossSell'] = (sell_trades['Return_Pct'] < 0).astype(np.int8)

                trade_df = (
                    sell_trades
                    .groupby('InvestorID', as_index=False)
                    .agg(
                        TotalSell=('InvestorID', 'size'),
                        PanicSell=('IsPanicSell', 'sum'),
                        LossSell=('IsLossSell', 'sum')
                    )
                )

        df_today_signals = drawdown_df[['InvestorID', 'DrawdownLevel']].merge(
            trade_df,
            on='InvestorID',
            how='left'
        )

        df_today_signals[['TotalSell', 'PanicSell', 'LossSell']] = (
            df_today_signals[['TotalSell', 'PanicSell', 'LossSell']]
            .fillna(0)
            .astype(np.int64)
        )

        df_today_signals['SellSpike'] = np.where(
            df_today_signals['TotalSell'] > 0,
            df_today_signals['PanicSell'] / df_today_signals['TotalSell'],
            0.0
        )
        df_today_signals['LossSensitivity'] = np.where(
            df_today_signals['TotalSell'] > 0,
            df_today_signals['LossSell'] / df_today_signals['TotalSell'],
            0.0
        )
        df_today_signals['PanicScore'] = fn_Calculate_Panic_Score(df_today_signals)
        df_today_signals['ObservationDate'] = current_date.normalize()

        df_today_signals = df_today_signals[
            ['InvestorID', 'ObservationDate', 'DrawdownLevel', 'SellSpike', 'LossSensitivity', 'PanicScore']
        ]

        daily_frames.append(df_today_signals)

    if not daily_frames:
        print("⚠️  Không có dữ liệu đủ để backfill signals.")
        return

    df_signals = pd.concat(daily_frames, ignore_index=True)

    print(f"\n📊 Kết quả backfill ({len(df_signals):,} rows, {df_signals['ObservationDate'].nunique():,} ngày):")
    print(df_signals[['DrawdownLevel', 'SellSpike', 'LossSensitivity', 'PanicScore']].describe().round(4))

    df_signals['PanicLevel'] = np.select(
        [df_signals['PanicScore'] >= 0.6, df_signals['PanicScore'] >= 0.4],
        ['High', 'Medium'],
        default='Low'
    )
    print("\n📈 Phân phối PanicLevel:")
    print(df_signals['PanicLevel'].value_counts())

    csv_path = DATA_RAW_DIR / 'behavior_signals.csv'
    df_signals.to_csv(csv_path, index=False)
    print(f"\n💾 Đã lưu CSV: {csv_path}")

    print("\n🚀 Đang backfill vào bảng BehaviorSignals (trigger sẽ tự fill Warnings)...")
    df_to_db = df_signals[['InvestorID', 'ObservationDate', 'DrawdownLevel', 'SellSpike', 'LossSensitivity', 'PanicScore']].copy()

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM Warnings"))
        conn.execute(text("DELETE FROM BehaviorSignals"))

    df_to_db.to_sql(
        'BehaviorSignals',
        con=engine,
        if_exists='append',
        index=False,
        chunksize=1000
    )

    with engine.connect() as conn:
        warning_count = conn.execute(text("SELECT COUNT(*) FROM Warnings")).scalar()

    print(f"\n✅ Đã push {len(df_to_db):,} BehaviorSignals")
    print(f"🔔 Trigger hiện có {warning_count:,} Warnings")
    print("\n🎉 HOÀN TẤT!")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    engine = create_engine(DB_CONNECTION_STR)
    build_and_push_behavior_signals(engine)
