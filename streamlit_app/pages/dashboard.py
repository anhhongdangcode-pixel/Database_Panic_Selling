import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils.db import run_query
from utils.charts import color_panic_score


def render(engine, role):
    """Render dashboard page."""
    st.title("📊 Dashboard")
    
    # Row 1 - 4 metric cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        df = run_query(engine, "SELECT COUNT(*) as count FROM Investors")
        count = int(df['count'].iloc[0]) if not df.empty else 0
        st.metric("👥 Tổng Investors", count)
    
    with col2:
        df = run_query(engine, """
            SELECT COUNT(*) as count FROM Warnings 
            WHERE WarningDate = (SELECT MAX(WarningDate) FROM Warnings)
        """)
        count = int(df['count'].iloc[0]) if not df.empty else 0
        st.metric("⚠️ Warnings hôm nay", count)
    
    with col3:
        df = run_query(engine, """
            SELECT COUNT(*) as count FROM Warnings 
            WHERE PanicLevel='High' AND WarningDate = (SELECT MAX(WarningDate) FROM Warnings)
        """)
        count = int(df['count'].iloc[0]) if not df.empty else 0
        st.metric("🔥 High Panic", count)
    
    with col4:
        df = run_query(engine, "SELECT MAX(TradeDate) as max_date FROM MarketData")
        date_str = str(df['max_date'].iloc[0]) if not df.empty else "N/A"
        st.metric("📅 Ngày mới nhất", date_str)
    
    st.divider()
    
    # Row 2 - 2 charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Phân bố Risk Profile")
        df = run_query(engine, "SELECT RiskProfile, COUNT(*) as count FROM Investors GROUP BY RiskProfile")
        if not df.empty:
            fig = px.pie(df, values='count', names='RiskProfile', title="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có dữ liệu")
    
    with col2:
        st.subheader("Panic Level hôm nay")
        df = run_query(engine, """
            SELECT * FROM vw_daily_panic_summary 
            WHERE ObservationDate = (SELECT MAX(ObservationDate) FROM vw_daily_panic_summary)
        """)
        if not df.empty:
            data = {
                'Level': ['High', 'Medium', 'Low'],
                'Count': [
                    int(df['HighCount'].iloc[0]),
                    int(df['MediumCount'].iloc[0]),
                    int(df['LowCount'].iloc[0])
                ]
            }
            colors = ['#FF0000', '#FFA500', '#008000']
            fig = px.bar(data, x='Level', y='Count', color='Level', 
                        color_discrete_map={'High': '#FF0000', 'Medium': '#FFA500', 'Low': '#008000'})
            fig.update_layout(showlegend=False, title="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có dữ liệu")
    
    st.divider()
    
    # Row 3 - Line chart full width
    st.subheader("Diễn biến NAV trung bình theo nhóm nhà đầu tư")
    df = run_query(engine, "SELECT * FROM vw_nav_by_riskprofile ORDER BY TradeDate")
    if not df.empty:
        fig = px.line(df, x='TradeDate', y='AvgNAV', color='RiskProfile', title="")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu")
    
    st.divider()
    
    # Row 4 - Top 10 investors by panic
    st.subheader("🔥 Top 10 Nhà đầu tư có PanicScore cao nhất")

    if role != 'Admin':
        st.info("Danh sách nhà đầu tư chi tiết chỉ dành cho Admin. Vai trò hiện tại chỉ xem được số liệu tổng hợp.")
    else:
        df = run_query(engine, """
            SELECT * FROM vw_investor_panic_latest 
            ORDER BY PanicScore DESC LIMIT 10
        """)
        
        if not df.empty:
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'PanicScore': st.column_config.NumberColumn(format="%.2f")
                }
            )
        else:
            st.info("Không có dữ liệu")
