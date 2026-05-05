"""
PUSH_TO_DB.PY
=============
Centralized database push script.
Handles all CSV → Database operations with proper FK ordering and date filtering.

Functions:
  - push_investors()
  - push_market_data()
  - push_trades()
  - push_portfolios()

Execution Order: investors → market_data → trades → portfolios
(respects foreign key constraints)
"""

import sys
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
import os

# --- SETUP IMPORT ---
current_file = Path(__file__).resolve()
src_path = current_file.parent.parent  # src/

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from config import DB_CONNECTION_STR, DATA_RAW_DIR

# ===================================
# CONFIGURATION
# ===================================
CUTOFF_DATE = '2025-08-31'  # Data cutoff

engine = create_engine(DB_CONNECTION_STR)

# ===================================
# 1. PUSH INVESTORS
# ===================================
def push_investors():
    """
    Load investors_dummy_data.csv → delete Warnings, BehaviorSignals, Trades, Portfolios, Investors
    (respect FK order) → append new investors
    """
    csv_path = DATA_RAW_DIR / "investors_dummy_data.csv"
    
    if not csv_path.exists():
        print(f"❌ Not found: {csv_path}")
        return False
    
    print(f"\n📤 [PUSH_INVESTORS] Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"   ✅ Loaded {len(df)} investors")
    
    try:
        with engine.begin() as conn:
            # Delete in FK order (reverse of creation)
            tables_to_delete = [
                'Warnings',
                'BehaviorSignals', 
                'Trades',
                'Portfolios',
                'Investors'
            ]
            
            print("   🧹 Deleting old data (FK order)...")
            for table in tables_to_delete:
                try:
                    conn.execute(text(f"DELETE FROM {table}"))
                    print(f"      → {table} cleared")
                except Exception as e:
                    print(f"      ⚠️  {table} error (may not exist): {str(e)[:50]}")
            
            conn.commit()
        
        # Append new investors
        print("   📥 Appending new investors...")
        df.to_sql('Investors', con=engine, if_exists='append', index=False)
        print(f"   ✅ {len(df)} investors pushed to Investors table")
        return True
        
    except Exception as e:
        print(f"   ❌ Error pushing investors: {e}")
        return False


# ===================================
# 2. PUSH MARKET DATA
# ===================================
def push_market_data():
    """
    Load final_market_data_2025.csv → calculate volatility if needed → 
    filter by CUTOFF_DATE → delete MarketData → append
    """
    csv_path = DATA_RAW_DIR / "final_market_data_2025.csv"
    
    if not csv_path.exists():
        print(f"❌ Not found: {csv_path}")
        return False
    
    print(f"\n📤 [PUSH_MARKET_DATA] Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"   ✅ Loaded {len(df)} market records")
    
    try:
        # Convert TradeDate to datetime
        if 'TradeDate' in df.columns:
            df['TradeDate'] = pd.to_datetime(df['TradeDate'])
        else:
            print("   ⚠️  No TradeDate column, trying 'Date'...")
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.rename(columns={'Date': 'TradeDate'}, inplace=True)
        
        # Calculate volatility if missing
        if 'Volatility' not in df.columns:
            print("   📊 Calculating Volatility (20-day rolling std per Ticker)...")
            
            # Ensure Pct_Change exists
            if 'Pct_Change' not in df.columns and 'ClosePrice' in df.columns:
                df = df.sort_values(['Ticker', 'TradeDate'])
                df['Pct_Change'] = df.groupby('Ticker')['ClosePrice'].pct_change()
            
            # Rolling std
            df['Volatility'] = (
                df.groupby('Ticker')['Pct_Change']
                .rolling(window=20, min_periods=1)
                .std()
                .reset_index(level=0, drop=True)
            )
        
        # Rename columns to match schema
        column_mapping = {
            'Pct_Change': 'DailyReturn',
            'MA20': 'MA_20'
        }
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)
                print(f"   📝 Renamed: {old_col} → {new_col}")
        
        # Filter by CUTOFF_DATE
        df_filtered = df[df['TradeDate'] <= CUTOFF_DATE].copy()
        print(f"   🔍 Filtered to {len(df_filtered)} records (≤ {CUTOFF_DATE})")
        
        # Drop duplicates (schema has UNIQUE INDEX on (TradeDate, Ticker))
        df_filtered = df_filtered.drop_duplicates(subset=['TradeDate', 'Ticker'], keep='first')
        print(f"   ✅ After deduplication: {len(df_filtered)} records")
        
        # Delete and append
        with engine.begin() as conn:
            print("   🧹 Clearing MarketData table...")
            conn.execute(text("DELETE FROM MarketData"))
            conn.commit()
        
        print("   📥 Appending market data...")
        df_filtered.to_sql('MarketData', con=engine, if_exists='append', index=False)
        print(f"   ✅ {len(df_filtered)} records pushed to MarketData table")
        return True
        
    except Exception as e:
        print(f"   ❌ Error pushing market data: {e}")
        return False


# ===================================
# 3. PUSH TRADES (from simulation)
# ===================================
def push_trades():
    """
    Load simulation_transactions.csv → filter by CUTOFF_DATE → 
    delete Trades → append
    """
    csv_path = DATA_RAW_DIR / "simulation_transactions.csv"
    
    if not csv_path.exists():
        print(f"   ℹ️  Not found (may not have run simulation yet): {csv_path}")
        return True  # Not critical
    
    print(f"\n📤 [PUSH_TRADES] Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"   ✅ Loaded {len(df)} trade records")
    
    try:
        # Convert TradeDate
        df['TradeDate'] = pd.to_datetime(df['TradeDate'])
        
        # Remove RiskProfile column if it exists (not in schema)
        if 'RiskProfile' in df.columns:
            print("   🧹 Removing RiskProfile column (not in Trades table)...")
            df = df.drop(columns=['RiskProfile'])
        
        # Filter by CUTOFF_DATE
        df_filtered = df[df['TradeDate'] <= CUTOFF_DATE].copy()
        print(f"   🔍 Filtered to {len(df_filtered)} records (≤ {CUTOFF_DATE})")
        
        # Delete and append
        with engine.begin() as conn:
            print("   🧹 Clearing Trades table...")
            conn.execute(text("DELETE FROM Trades"))
            conn.commit()
        
        print("   📥 Appending trades...")
        df_filtered.to_sql('Trades', con=engine, if_exists='append', index=False)
        print(f"   ✅ {len(df_filtered)} trades pushed to Trades table")
        return True
        
    except Exception as e:
        print(f"   ❌ Error pushing trades: {e}")
        return False


# ===================================
# 4. PUSH PORTFOLIOS (from simulation)
# ===================================
def push_portfolios():
    """
    Load simulation_portfolio_history.csv → map old columns to new schema → 
    filter by CUTOFF_DATE → delete Portfolios → append
    """
    csv_path = DATA_RAW_DIR / "simulation_portfolio_history.csv"
    
    if not csv_path.exists():
        print(f"   ℹ️  Not found (may not have run simulation yet): {csv_path}")
        return True  # Not critical
    
    print(f"\n📤 [PUSH_PORTFOLIOS] Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"   ✅ Loaded {len(df)} portfolio records")
    
    try:
        # Rename columns (old → new schema)
        column_mapping = {
            'Date': 'TradeDate',
            'Investor_ID': 'InvestorID',
            'Total_Asset': 'NAV',
            'Cash_Balance': 'CashBalance'
        }
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)
                print(f"   📝 Renamed: {old_col} → {new_col}")
        
        # Convert TradeDate
        df['TradeDate'] = pd.to_datetime(df['TradeDate'])
        
        # Filter by CUTOFF_DATE
        df_filtered = df[df['TradeDate'] <= CUTOFF_DATE].copy()
        print(f"   🔍 Filtered to {len(df_filtered)} records (≤ {CUTOFF_DATE})")
        
        # Delete and append
        with engine.begin() as conn:
            print("   🧹 Clearing Portfolios table...")
            conn.execute(text("DELETE FROM Portfolios"))
            conn.commit()
        
        print("   📥 Appending portfolio snapshots...")
        df_filtered.to_sql('Portfolios', con=engine, if_exists='append', index=False)
        print(f"   ✅ {len(df_filtered)} portfolio records pushed to Portfolios table")
        return True
        
    except Exception as e:
        print(f"   ❌ Error pushing portfolios: {e}")
        return False


# ===================================
# MAIN
# ===================================
def main():
    """
    Execute all pushes in order:
    1. Investors (clears dependent tables first)
    2. Market Data
    3. Trades (depends on Investors)
    4. Portfolios (depends on Investors)
    """
    print("="*60)
    print("🚀 PUSH TO DATABASE - CONSOLIDATED PIPELINE")
    print("="*60)
    
    results = []
    
    # Step 1: Investors
    if not push_investors():
        print("\n❌ Failed at investors step - aborting")
        return False
    results.append(("Investors", True))
    
    # Step 2: Market Data
    if not push_market_data():
        print("\n❌ Failed at market data step - aborting")
        return False
    results.append(("MarketData", True))
    
    # Step 3: Trades (non-critical)
    push_trades()
    results.append(("Trades", True))
    
    # Step 4: Portfolios (non-critical)
    push_portfolios()
    results.append(("Portfolios", True))
    
    # Summary
    print("\n" + "="*60)
    print("✅ PUSH COMPLETED")
    print("="*60)
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
