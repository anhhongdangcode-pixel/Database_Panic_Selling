import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from config import DB_CONNECTION_STR, DATA_RAW_DIR

def calculate_behavioral_features(investor_id, transactions_df, portfolio_df, market_df):
    """
    Tính toán behavioral features cho 1 investor
    Chỉ dựa trên Market Regime (không dùng technical indicators)
    """
    
    # Filter data
    inv_trans = transactions_df[transactions_df['Investor_ID'] == investor_id].copy()
    inv_port = portfolio_df[portfolio_df['Investor_ID'] == investor_id].copy()
    
    if len(inv_trans) == 0:
        return None
    
    # Merge với market regime
    inv_trans = inv_trans.merge(
        market_df[['Date', 'Ticker', 'Market_Regime']], 
        on=['Date', 'Ticker'], 
        how='left'
    )
    
    features = {'Investor_ID': investor_id}
    
    # Separate buy/sell
    buy_trans = inv_trans[inv_trans['Action'] == 'BUY']
    sell_trans = inv_trans[inv_trans['Action'] == 'SELL']
    
    # =============================================
    # GROUP 1: CHASING BEHAVIOR (5 features)
    # =============================================
    
    if len(buy_trans) > 0:
        # F1: Explosion Buy Ratio (Core FOMO signal)
        explosion_buys = (buy_trans['Market_Regime'] == 'EXPLOSION').sum()
        features['explosion_buy_ratio'] = explosion_buys / len(buy_trans)
        
        # F2: Distribution Buy Ratio (Trap signal)
        dist_buys = (buy_trans['Market_Regime'] == 'SIDEWAY_DISTRIBUTION').sum()
        features['distribution_buy_ratio'] = dist_buys / len(buy_trans)
        
        # F3: Chasing Score (Combined)
        features['chasing_score'] = features['explosion_buy_ratio'] + features['distribution_buy_ratio']
        
        # F4: Accumulation Buy Ratio (Good behavior)
        accum_buys = (buy_trans['Market_Regime'] == 'SIDEWAY_ACCUMULATION').sum()
        features['accumulation_buy_ratio'] = accum_buys / len(buy_trans)
        
        # F5: Panic Buy Ratio (Catching falling knife)
        panic_buys = (buy_trans['Market_Regime'] == 'PANIC').sum()
        features['panic_buy_ratio'] = panic_buys / len(buy_trans)
    else:
        features['explosion_buy_ratio'] = 0
        features['distribution_buy_ratio'] = 0
        features['chasing_score'] = 0
        features['accumulation_buy_ratio'] = 0
        features['panic_buy_ratio'] = 0
    
    # =============================================
    # GROUP 2: TRADE ACCELERATION (4 features)
    # =============================================
    
    # Get regime days
    explosion_days = market_df[market_df['Market_Regime'] == 'EXPLOSION']['Date'].unique()
    panic_days = market_df[market_df['Market_Regime'] == 'PANIC']['Date'].unique()
    normal_days = market_df[market_df['Market_Regime'] == 'SIDEWAY_ACCUMULATION']['Date'].unique()
    
    # F6: Explosion Trade Acceleration
    explosion_trades = inv_trans[inv_trans['Date'].isin(explosion_days)]
    normal_trades = inv_trans[inv_trans['Date'].isin(normal_days)]
    
    trades_per_day_explosion = len(explosion_trades) / len(explosion_days) if len(explosion_days) > 0 else 0
    trades_per_day_normal = len(normal_trades) / len(normal_days) if len(normal_days) > 0 else 0.01
    
    features['explosion_trade_acceleration'] = trades_per_day_explosion / trades_per_day_normal
    
    # F7: Panic Trade Acceleration
    panic_trades = inv_trans[inv_trans['Date'].isin(panic_days)]
    trades_per_day_panic = len(panic_trades) / len(panic_days) if len(panic_days) > 0 else 0
    
    features['panic_trade_acceleration'] = trades_per_day_panic / trades_per_day_normal
    
    # F8-9: Weekly Trade Volatility
    inv_trans['Week'] = pd.to_datetime(inv_trans['Date']).dt.isocalendar().week
    weekly_trades = inv_trans.groupby('Week').size()
    
    if len(weekly_trades) > 1:
        features['trade_freq_std'] = weekly_trades.std()
        features['trade_freq_cv'] = weekly_trades.std() / weekly_trades.mean()
    else:
        features['trade_freq_std'] = 0
        features['trade_freq_cv'] = 0
    
    # =============================================
    # GROUP 3: HOLDING INCONSISTENCY (4 features)
    # =============================================
    
    if len(sell_trans) > 0:
        # F10: Premature Exit Rate (Sell with profit < 5%)
        premature_exits = ((sell_trans['Return_Pct'] > 0) & (sell_trans['Return_Pct'] < 0.05)).sum()
        features['premature_exit_rate'] = premature_exits / len(sell_trans)
        
        # F11: Explosion Sell Ratio (Sell during hot market)
        explosion_sells = (sell_trans['Market_Regime'] == 'EXPLOSION').sum()
        features['explosion_sell_ratio'] = explosion_sells / len(sell_trans)
    else:
        features['premature_exit_rate'] = 0
        features['explosion_sell_ratio'] = 0
    
    # F12-13: Holding Period
    holding_periods = []
    for ticker in inv_trans['Ticker'].unique():
        ticker_trans = inv_trans[inv_trans['Ticker'] == ticker].sort_values('Date')
        buys = ticker_trans[ticker_trans['Action'] == 'BUY']
        sells = ticker_trans[ticker_trans['Action'] == 'SELL']
        
        for buy_date in buys['Date'].values:
            next_sell = sells[sells['Date'] > buy_date]
            if len(next_sell) > 0:
                sell_date = next_sell.iloc[0]['Date']
                holding_days = (pd.to_datetime(sell_date) - pd.to_datetime(buy_date)).days
                holding_periods.append(holding_days)
    
    features['avg_holding_period'] = np.mean(holding_periods) if len(holding_periods) > 0 else 0
    
    quick_sells = [hp for hp in holding_periods if hp <= 3]
    features['quick_sell_ratio'] = len(quick_sells) / len(holding_periods) if len(holding_periods) > 0 else 0
    
    # =============================================
    # GROUP 4: DRAWDOWN SENSITIVITY (4 features)
    # =============================================
    
    if len(inv_port) > 0:
        inv_port = inv_port.sort_values('Date')
        inv_port['Cummax'] = inv_port['Total_Asset'].cummax()
        inv_port['Drawdown'] = (inv_port['Total_Asset'] - inv_port['Cummax']) / inv_port['Cummax']
        
        # F14: Max Drawdown
        features['max_drawdown'] = inv_port['Drawdown'].min()
        
        # F15: Trade When Drawdown > 10%
        deep_drawdown_days = inv_port[inv_port['Drawdown'] < -0.10]['Date'].values
        trades_during_drawdown = inv_trans[inv_trans['Date'].isin(deep_drawdown_days)]
        
        features['drawdown_trade_count'] = len(trades_during_drawdown)
        features['drawdown_trade_ratio'] = len(trades_during_drawdown) / len(inv_trans)
        
        # F16: Panic Sell During Drawdown
        panic_sells_in_dd = trades_during_drawdown[
            (trades_during_drawdown['Action'] == 'SELL') & 
            (trades_during_drawdown['Market_Regime'] == 'PANIC')
        ]
        
        features['drawdown_panic_sell_ratio'] = (
            len(panic_sells_in_dd) / len(trades_during_drawdown) 
            if len(trades_during_drawdown) > 0 else 0
        )
    else:
        features['max_drawdown'] = 0
        features['drawdown_trade_count'] = 0
        features['drawdown_trade_ratio'] = 0
        features['drawdown_panic_sell_ratio'] = 0
    
    # =============================================
    # GROUP 5: PERFORMANCE METRICS (6 features)
    # =============================================
    
    # F17: Total Trades
    features['total_trades'] = len(inv_trans)
    
    # F18: Buy/Sell Ratio
    features['buy_sell_ratio'] = len(buy_trans) / len(sell_trans) if len(sell_trans) > 0 else 0
    
    if len(sell_trans) > 0:
        # F19: Win Rate
        features['win_rate'] = (sell_trans['Return_Pct'] > 0).sum() / len(sell_trans)
        
        # F20-21: Avg Profit/Loss
        winning_trades = sell_trans[sell_trans['Return_Pct'] > 0]
        losing_trades = sell_trans[sell_trans['Return_Pct'] < 0]
        
        features['avg_profit'] = winning_trades['Return_Pct'].mean() if len(winning_trades) > 0 else 0
        features['avg_loss'] = losing_trades['Return_Pct'].mean() if len(losing_trades) > 0 else 0
        
        # F22: Risk-Reward Ratio
        features['risk_reward_ratio'] = (
            abs(features['avg_profit'] / features['avg_loss']) 
            if features['avg_loss'] != 0 else 0
        )
    else:
        features['win_rate'] = 0
        features['avg_profit'] = 0
        features['avg_loss'] = 0
        features['risk_reward_ratio'] = 0
    
    # =============================================
    # GROUP 6: PORTFOLIO METRICS (2 features)
    # =============================================
    
    if len(inv_port) > 0:
        # F23: Sharpe Ratio
        inv_port['Daily_Return'] = inv_port['Total_Asset'].pct_change()
        sharpe = (
            inv_port['Daily_Return'].mean() / inv_port['Daily_Return'].std() 
            if inv_port['Daily_Return'].std() > 0 else 0
        )
        features['sharpe_ratio'] = sharpe
        
        # F24: Total Return
        initial = inv_port['Total_Asset'].iloc[0]
        final = inv_port['Total_Asset'].iloc[-1]
        features['total_return'] = (final - initial) / initial
    else:
        features['sharpe_ratio'] = 0
        features['total_return'] = 0
    
    return features


def build_feature_dataset():
    """
    Tạo dataset features cho tất cả investors
    """
    print(" Đang kết nối database...")
    engine = create_engine(DB_CONNECTION_STR)
    
    # Load data
    print(" Đang tải dữ liệu...")
    transactions_df = pd.read_sql("SELECT * FROM transactions", engine)
    portfolio_df = pd.read_sql("SELECT * FROM portfolio_history", engine)
    market_df = pd.read_sql("SELECT * FROM Simulation_Market_Regimes", engine)
    investors_df = pd.read_sql("SELECT Investor_ID, Investor_Type FROM investors", engine)
    
    print(" Đang chuẩn hóa định dạng ngày tháng...")
    transactions_df['Date'] = pd.to_datetime(transactions_df['Date'])
    portfolio_df['Date'] = pd.to_datetime(portfolio_df['Date'])
    market_df['Date'] = pd.to_datetime(market_df['Date'])
    
    print(f" Đã tải: {len(transactions_df)} transactions, {len(investors_df)} investors")
    
    # Tính features
    print("\n Đang tính features cho từng investor...")
    feature_list = []
    
    from tqdm import tqdm
    for _, investor in tqdm(investors_df.iterrows(), total=len(investors_df)):
        inv_id = investor['Investor_ID']
        
        features = calculate_behavioral_features(
            inv_id, transactions_df, portfolio_df, market_df
        )
        
        if features:
            features['Investor_Type'] = investor['Investor_Type']
            feature_list.append(features)
    
    # Tạo DataFrame
    feature_df = pd.DataFrame(feature_list)
    
    # Sắp xếp lại columns
    label_col = ['Investor_ID', 'Investor_Type']
    feature_cols = [col for col in feature_df.columns if col not in label_col]
    feature_df = feature_df[label_col + feature_cols]
    
    # Lưu file
    output_path = DATA_RAW_DIR / 'behavioral_features.csv'
    feature_df.to_csv(output_path, index=False)
    
    print(f"\n Đã tạo {len(feature_df)} investor features!")
    print(f"💾 File saved: {output_path}")
    print(f"📏 Số features: {len(feature_cols)}")
    
    # Summary
    print("\n FEATURE SUMMARY:")
    print(feature_df[label_col + feature_cols[:5]].head())
    
    print("\n DISTRIBUTION BY TYPE:")
    print(feature_df['Investor_Type'].value_counts())
    
    return feature_df


if __name__ == "__main__":
    feature_df = build_feature_dataset()