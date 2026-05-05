"""
next_day.py
===========
Push dữ liệu cho ngày giao dịch tiếp theo từ CSV vào database, sau đó gọi
stored procedure xử lý EOD và kiểm tra warnings mới được tạo.
"""

import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text


# --- Import setup ---
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
if FILE_DIR not in sys.path:
    sys.path.insert(0, FILE_DIR)

from config import DB_CONNECTION_STR, DATA_RAW_DIR


# --- CSV paths ---
MARKET_CSV = DATA_RAW_DIR / "final_market_data_2025.csv"
TRADES_CSV = DATA_RAW_DIR / "simulation_transactions.csv"
PORTFOLIO_CSV = DATA_RAW_DIR / "simulation_portfolio_history.csv"


MARKET_SCHEMA_COLS = [
    "TradeDate",
    "Ticker",
    "Open",
    "High",
    "Low",
    "ClosePrice",
    "Volume",
    "DailyReturn",
    "Volatility",
    "MA_Volume_30",
    "RSI_14",
    "MA_20",
    "Market_Regime",
]


def _ensure_timestamp(value):
    return pd.Timestamp(value).normalize()


def _load_csv_with_date(path, date_col="TradeDate"):
    df = pd.read_csv(path)
    if date_col not in df.columns:
        raise KeyError(f"Missing date column '{date_col}' in {path}")
    df[date_col] = pd.to_datetime(df[date_col])
    return df


def get_next_date(engine):
    """Lấy ngày giao dịch tiếp theo sau ngày lớn nhất đang có trong MarketData."""
    with engine.connect() as conn:
        last_date = conn.execute(text("SELECT MAX(TradeDate) FROM MarketData")).scalar()

    if last_date is None:
        print("MarketData chưa có dữ liệu. Sẽ lấy ngày đầu tiên trong CSV.")
        last_date = pd.Timestamp.min
    else:
        last_date = pd.Timestamp(last_date)

    market_df = _load_csv_with_date(MARKET_CSV)
    future_dates = (
        market_df.loc[market_df["TradeDate"] > last_date, "TradeDate"]
        .drop_duplicates()
        .sort_values()
    )

    if future_dates.empty:
        print("Đã hết data tương lai")
        return None

    return pd.Timestamp(future_dates.iloc[0]).normalize()


def _prepare_market_for_date(target_date):
    market_df = _load_csv_with_date(MARKET_CSV)
    day_df = market_df.loc[market_df["TradeDate"] == target_date].copy()

    if day_df.empty:
        return day_df

    # CSV nguồn có thể lặp (TradeDate, Ticker) nhiều lần, nhưng schema MarketData
    # chỉ cho phép một bản ghi duy nhất cho mỗi cặp này.
    before_dedup = len(day_df)
    day_df = day_df.drop_duplicates(subset=["TradeDate", "Ticker"], keep="first")
    after_dedup = len(day_df)
    if after_dedup != before_dedup:
        print(f"   -> MarketData dedup: {before_dedup} -> {after_dedup}")

    rename_map = {
        "Pct_Change": "DailyReturn",
        "MA20": "MA_20",
    }
    day_df = day_df.rename(columns=rename_map)
    day_df["Volatility"] = None

    for column in MARKET_SCHEMA_COLS:
        if column not in day_df.columns:
            day_df[column] = None

    day_df = day_df[MARKET_SCHEMA_COLS].copy()
    return day_df


def _load_and_filter_day(csv_path, target_date, date_col="TradeDate"):
    df = _load_csv_with_date(csv_path, date_col=date_col)
    return df.loc[df[date_col] == target_date].copy()


def push_next_day(target_date, engine):
    """Push MarketData, Trades, Portfolios cho target_date rồi gọi procedure EOD."""
    target_date = _ensure_timestamp(target_date)

    # Step 1 - MarketData
    print(f"\n📈 Push MarketData cho {target_date.date()}...")
    market_day_df = _prepare_market_for_date(target_date)
    print(f"   -> {len(market_day_df):,} dòng market")

    if not market_day_df.empty:
        with engine.begin() as conn:
            market_day_df.to_sql("MarketData", con=conn, if_exists="append", index=False)

    # Step 2 - Trades
    print(f"\n💱 Push Trades cho {target_date.date()}...")
    trades_day_df = _load_and_filter_day(TRADES_CSV, target_date)

    if "RiskProfile" in trades_day_df.columns:
        trades_day_df = trades_day_df.drop(columns=["RiskProfile"])

    print(f"   -> {len(trades_day_df):,} lệnh giao dịch")

    if not trades_day_df.empty:
        with engine.begin() as conn:
            trades_day_df.to_sql("Trades", con=conn, if_exists="append", index=False)

    # Step 3 - Portfolios
    print(f"\n📊 Push Portfolios cho {target_date.date()}...")
    portfolio_day_df = _load_and_filter_day(PORTFOLIO_CSV, target_date)
    print(f"   -> {len(portfolio_day_df):,} snapshot portfolio")

    if not portfolio_day_df.empty:
        with engine.begin() as conn:
            portfolio_day_df.to_sql("Portfolios", con=conn, if_exists="append", index=False)

    # Step 4 - Stored procedure
    print(f"\n⚙️  Gọi stored procedure cho {target_date.date()}...")
    with engine.begin() as conn:
        proc_result = conn.execute(
            text("CALL sp_daily_eod_process(:d)"),
            {"d": str(target_date.date())}
        )

        proc_rows = []
        if proc_result.returns_rows:
            proc_rows = proc_result.fetchall()

        if proc_rows:
            print("   -> Kết quả procedure:")
            for row in proc_rows:
                print(f"      {row}")
        else:
            print("   -> Procedure không trả về dòng dữ liệu nào")

    # Step 5 - Warnings mới
    with engine.connect() as conn:
        warning_count = conn.execute(
            text("SELECT COUNT(*) FROM Warnings WHERE WarningDate = :d"),
            {"d": str(target_date.date())}
        ).scalar()

    print(f"\n🔔 Warnings được trigger sinh ra: {warning_count:,}")


def main():
    engine = create_engine(DB_CONNECTION_STR)

    next_date = get_next_date(engine)
    if next_date is None:
        return

    print(f"\n🗓️ Đang xử lý ngày: {next_date.date()}")
    push_next_day(next_date, engine)
    print("\n✅ Hoàn tất xử lý next day")


if __name__ == "__main__":
    main()