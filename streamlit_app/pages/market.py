import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from utils.db import run_query


def render(engine, role):
    """Render market overview page."""
    
    # Only Admin can access
    if role != 'Admin':
        st.warning("⚠️ Không có quyền truy cập trang này. Chỉ Admin mới có thể xem.")
        return
    
    st.title("📈 Tổng quan Thị trường")
    
    # Stock ticker selector
    selected_ticker = st.selectbox(
        "Chọn mã cổ phiếu",
        ['VIC', 'VHM', 'HPG', 'FPT', 'VCB', 'SSI', 'VPB', 'BCM', 'MSN']
    )
    
    st.divider()
    
    # Get market data for selected ticker
    df = run_query(engine, """
        SELECT TradeDate, Open, High, Low, ClosePrice, Volume, Market_Regime 
        FROM MarketData 
        WHERE Ticker = :ticker ORDER BY TradeDate
    """, {'ticker': selected_ticker})
    
    if not df.empty:
        # Rename column for plotly
        df = df.rename(columns={'ClosePrice': 'Close'})
        
        # Create candlestick chart with volume
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3]
        )
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df['TradeDate'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='Price'
            ),
            row=1, col=1
        )
        
        # Volume bars
        colors = ['red' if close < open_ else 'green' 
                 for close, open_ in zip(df['Close'], df['Open'])]
        fig.add_trace(
            go.Bar(x=df['TradeDate'], y=df['Volume'], name='Volume', 
                  marker_color=colors, showlegend=False),
            row=2, col=1
        )
        
        # Add background rects for market regimes
        regime_colors = {
            'PANIC': 'rgba(255, 0, 0, 0.2)',
            'EXPLOSION': 'rgba(128, 0, 128, 0.2)',
            'SIDEWAY_ACCUMULATION': 'rgba(0, 128, 0, 0.2)',
            'SIDEWAY_DISTRIBUTION': 'rgba(255, 165, 0, 0.2)'
        }
        
        # Add regime background
        current_regime = None
        start_date = None
        
        for idx, row in df.iterrows():
            regime = row['Market_Regime']
            if regime != current_regime:
                if current_regime is not None and start_date is not None:
                    fig.add_vrect(
                        x0=start_date, x1=row['TradeDate'],
                        fillcolor=regime_colors.get(current_regime, 'rgba(0,0,0,0.1)'),
                        layer="below",
                        line_width=0,
                        row=1, col=1
                    )
                current_regime = regime
                start_date = row['TradeDate']
        
        # Add final regime
        if current_regime is not None and start_date is not None:
            fig.add_vrect(
                x0=start_date, x1=df['TradeDate'].iloc[-1],
                fillcolor=regime_colors.get(current_regime, 'rgba(0,0,0,0.1)'),
                layer="below",
                line_width=0,
                row=1, col=1
            )
        
        fig.update_layout(
            title=f"Candlestick Chart - {selected_ticker}",
            yaxis_title='Price',
            yaxis2_title='Volume',
            height=700,
            xaxis_rangeslider_visible=False,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        # Statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Số ngày theo Market Regime")
            regime_counts = df['Market_Regime'].value_counts().reset_index()
            regime_counts.columns = ['Market_Regime', 'Số ngày']
            st.dataframe(regime_counts, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("📈 Avg Daily Return theo Regime")
            df['DailyReturn'] = (df['Close'] - df['Open']) / df['Open'] * 100
            daily_return_by_regime = df.groupby('Market_Regime')['DailyReturn'].mean().reset_index()
            daily_return_by_regime.columns = ['Market_Regime', 'Avg DailyReturn %']
            
            fig_bar = px.bar(daily_return_by_regime, 
                           x='Market_Regime', y='Avg DailyReturn %',
                           title="")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.error(f"Không tìm thấy dữ liệu cho {selected_ticker}")
