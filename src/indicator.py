import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-whitegrid')

def basic_feature_engineering(df, ma_window=20, rsi_window=14):
    df = df.sort_values(['Ticker', 'Date'])

    # Percentage change
    df['Pct_Change'] = (df.groupby('Ticker')['Close'].pct_change() * 100).round(2)
    # Calculate MA20
    df['MA20'] = df.groupby('Ticker')['Close'].transform(
        lambda x: x.rolling(window=ma_window).mean()
    ).round(2)
    # Calculate MA Volume 30
    df['MA_Volume_30'] = df.groupby('Ticker')['Volume'].transform(lambda x: x.rolling(window=30).mean()).round(2)

    # RSI Wilder (TradingView equivalent)
    def calculate_rsi_tradingview(series, period=14):
        delta = series.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        # TradingView uses RMA (Relative Moving Average)
        # Equivalent to ewm with alpha = 1/period and adjust=False
        avg_gain = gain.ewm(
            alpha=1 / period,
            min_periods=period,
            adjust=False
        ).mean()

        avg_loss = loss.ewm(
            alpha=1 / period,
            min_periods=period,
            adjust=False
        ).mean()

        rs = avg_gain / avg_loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    # IMPORTANT: RSI must be calculated on the FULL dataset
    # BEFORE slicing the last 15 days for plotting
    df['RSI_14'] = df.groupby('Ticker')['Close'].transform(
        lambda x: calculate_rsi_tradingview(x, rsi_window)
    ).round(2)

    return df
