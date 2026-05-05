import streamlit as st
import plotly.express as px
from utils.db import run_query


def render(engine, role):
    """Render behavioral analytics page."""
    
    # Admin and Analyst can access
    if role not in ['Admin', 'Analyst']:
        st.warning("⚠️ Không có quyền truy cập trang này.")
        return
    
    st.title("📊 Phân tích Hành vi Nhà đầu tư")
    
    # Section 1 - Behavioral Signals Distribution
    st.subheader("📊 Phân phối Behavioral Signals")
    
    df_all = run_query(engine, "SELECT * FROM vw_investor_panic_latest")
    
    if not df_all.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig = px.histogram(df_all, x='DrawdownLevel', color='RiskProfile', 
                             barmode='overlay', opacity=0.6, title="Drawdown Level")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.histogram(df_all, x='SellSpike', color='RiskProfile', 
                             barmode='overlay', opacity=0.6, title="Sell Spike")
            st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            fig = px.histogram(df_all, x='LossSensitivity', color='RiskProfile', 
                             barmode='overlay', opacity=0.6, title="Loss Sensitivity")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu")
    
    st.divider()
    
    # Section 2 - Correlation Analysis
    st.subheader("🔗 Phân tích tương quan")
    
    if not df_all.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            hover_data = ['RiskProfile'] if role != 'Admin' else ['InvestorID', 'RiskProfile']
            fig = px.scatter(df_all, 
                           x='SellSpike', y='DrawdownLevel',
                           color='PanicScore',
                           size='LossSensitivity',
                           hover_data=hover_data,
                           color_continuous_scale='RdYlGn_r',
                           title="Sell Spike vs Drawdown Level")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.box(df_all, x='RiskProfile', y='PanicScore', 
                        color='RiskProfile', title="PanicScore by RiskProfile")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu")
    
    st.divider()
    
    # Section 3 - Warning Timeline
    st.subheader("⏰ Timeline Cảnh báo")
    
    df_daily = run_query(engine, "SELECT * FROM vw_daily_panic_summary ORDER BY ObservationDate")
    
    if not df_daily.empty:
        # Create figure with secondary y-axis
        fig = px.line(df_daily, x='ObservationDate', 
                     y=['HighCount', 'MediumCount', 'LowCount'],
                     title="")
        
        # Update trace colors
        fig.data[0].line.color = '#FF0000'  # Red for High
        fig.data[1].line.color = '#FFA500'  # Orange for Medium
        fig.data[2].line.color = '#008000'  # Green for Low
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Không có dữ liệu")
    
    st.divider()
    
    # Section 4 - Warnings Detail
    st.subheader("🔥 Chi tiết Cảnh báo")

    if role != 'Admin':
        st.info("Bảng cảnh báo chi tiết chỉ dành cho Admin. Analyst chỉ xem được các biểu đồ tổng hợp.")
    else:
        df_warnings = run_query(engine, """
            SELECT * FROM vw_warning_dashboard 
            ORDER BY Confidence DESC LIMIT 200
        """)
        
        if not df_warnings.empty:
            st.dataframe(df_warnings, use_container_width=True, hide_index=True)
        else:
            st.info("Không có dữ liệu")
