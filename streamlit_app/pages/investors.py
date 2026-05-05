import streamlit as st
import plotly.express as px
from utils.db import run_query
from utils.charts import color_panic_score, color_trade_type, color_reason


def render(engine, role):
    """Render investors management page."""
    
    # Only Admin can access
    if role != 'Admin':
        st.warning("⚠️ Không có quyền truy cập trang này. Chỉ Admin mới có thể xem.")
        return
    
    st.title("👥 Quản lý Nhà đầu tư")
    
    # Left column - Filter panel (1/3)
    # Right column - Results (2/3)
    col_filter, col_results = st.columns([1, 2])
    
    with col_filter:
        st.subheader("🔍 Bộ lọc")
        
        search_term = st.text_input("Tìm theo tên hoặc ID", "")
        filter_risk = st.selectbox("RiskProfile", 
                                   ["Tất cả", "FOMO", "RATIONAL", "NOISE"])
        min_panic = st.slider("PanicScore tối thiểu", 0.0, 1.0, 0.0, step=0.05)
        search_btn = st.button("🔍 Tìm kiếm", type="primary", use_container_width=True)
    
    with col_results:
        st.subheader("📋 Kết quả")
        
        # Build dynamic query
        query = "SELECT * FROM vw_investor_panic_latest WHERE 1=1"
        params = {}
        
        if search_term and search_btn:
            query += " AND (InvestorID LIKE :search OR InvestorName LIKE :search)"
            params['search'] = f"%{search_term}%"
        
        if filter_risk != "Tất cả" and search_btn:
            query += " AND RiskProfile = :risk"
            params['risk'] = filter_risk
        
        if min_panic > 0 and search_btn:
            query += " AND PanicScore >= :min_panic"
            params['min_panic'] = min_panic
        
        query += " ORDER BY PanicScore DESC"
        
        # Execute query
        if search_btn:
            df_results = run_query(engine, query, params)
        else:
            df_results = run_query(engine, "SELECT * FROM vw_investor_panic_latest ORDER BY PanicScore DESC LIMIT 100")
        
        if not df_results.empty:
            st.dataframe(df_results, use_container_width=True, hide_index=True)
            
            # Investor detail selector
            investor_list = df_results['InvestorID'].unique().tolist()
            selected_investor = st.selectbox(
                "Chọn Investor để xem chi tiết",
                investor_list,
                key="investor_selector"
            )
            
            if selected_investor:
                st.divider()
                st.subheader(f"📊 Chi tiết - {selected_investor}")
                
                # Three tabs for detailed view
                tab1, tab2, tab3 = st.tabs(["📈 NAV History", "💰 Trade History", "📉 PanicScore Timeline"])
                
                # Tab 1 - NAV History
                with tab1:
                    df_nav = run_query(engine, """
                        SELECT TradeDate, NAV FROM Portfolios 
                        WHERE InvestorID = :id ORDER BY TradeDate
                    """, {'id': selected_investor})
                    
                    if not df_nav.empty:
                        fig = px.line(df_nav, x='TradeDate', y='NAV', title="NAV History", markers=True)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Không có dữ liệu")
                
                # Tab 2 - Trade History
                with tab2:
                    df_trades = run_query(engine, """
                        SELECT * FROM vw_investor_trade_history 
                        WHERE InvestorID = :id ORDER BY TradeDate DESC LIMIT 100
                    """, {'id': selected_investor})
                    
                    if not df_trades.empty:
                        st.dataframe(df_trades, use_container_width=True, hide_index=True)
                    else:
                        st.info("Không có dữ liệu")
                
                # Tab 3 - PanicScore Timeline
                with tab3:
                    df_signals = run_query(engine, """
                        SELECT ObservationDate, DrawdownLevel, SellSpike, 
                               LossSensitivity, PanicScore FROM BehaviorSignals 
                        WHERE InvestorID = :id ORDER BY ObservationDate
                    """, {'id': selected_investor})
                    
                    if not df_signals.empty:
                        fig = px.line(df_signals, x='ObservationDate', 
                                     y=['DrawdownLevel', 'SellSpike', 'LossSensitivity', 'PanicScore'],
                                     title="")
                        # Add threshold line
                        fig.add_hline(y=0.6, line_dash="dash", line_color="red", 
                                     annotation_text="High Panic Threshold")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Không có dữ liệu")
        else:
            st.info("Không tìm thấy kết quả nào")
