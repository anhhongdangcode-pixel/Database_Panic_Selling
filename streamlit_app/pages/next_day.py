import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from utils.db import run_query

# Add src to path to import functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

try:
    from next_day import get_next_date, push_next_day
except ImportError:
    st.error("❌ Không thể import functions từ next_day.py")
    get_next_date = None
    push_next_day = None


def render(engine, role):
    """Render next day simulation page."""
    
    # Only Admin and Analyst can access
    if role not in ['Admin', 'Analyst']:
        st.warning("⚠️ Không có quyền truy cập trang này.")
        return
    
    st.title("🚀 Mô phỏng Ngày tiếp theo")
    
    if get_next_date is None or push_next_day is None:
        st.error("❌ Lỗi: Không thể load simulation functions")
        return
    
    # Row 1 - Status cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        df = run_query(engine, "SELECT MAX(TradeDate) as max_date FROM MarketData")
        last_date = str(df['max_date'].iloc[0]) if not df.empty else "N/A"
        st.metric("📅 Ngày cuối trong DB", last_date)
    
    with col2:
        try:
            csv_path = Path(__file__).parent.parent.parent / 'data' / 'raw' / 'final_market_data_2025.csv'
            if csv_path.exists():
                df_future = pd.read_csv(csv_path)
                
                # Get last date in DB
                df_last = run_query(engine, "SELECT MAX(TradeDate) as max_date FROM MarketData")
                if not df_last.empty:
                    last_db_date = pd.to_datetime(df_last['max_date'].iloc[0])
                    df_future['TradeDate'] = pd.to_datetime(df_future['TradeDate'])
                    future_count = len(df_future[df_future['TradeDate'] > last_db_date])
                    st.metric("🔮 Còn X ngày tương lai", future_count)
                else:
                    st.metric("🔮 Còn X ngày tương lai", "N/A")
            else:
                st.metric("🔮 Còn X ngày tương lai", "N/A")
        except Exception as e:
            st.metric("🔮 Còn X ngày tương lai", "Error")
    
    with col3:
        df = run_query(engine, "SELECT COUNT(DISTINCT TradeDate) as count FROM MarketData")
        count = int(df['count'].iloc[0]) if not df.empty else 0
        st.metric("📊 Tổng ngày đã có", count)
    
    st.divider()
    
    # Main simulation button
    if st.button("▶ Simulate Next Day", type="primary", use_container_width=True):
        with st.spinner("⏳ Đang xử lý ngày mới..."):
            try:
                next_date = get_next_date(engine)
                
                if next_date is None:
                    st.warning("⚠️ Đã hết data tương lai. Không có ngày tiếp theo để mô phỏng.")
                else:
                    # Run simulation
                    push_next_day(next_date, engine)
                    
                    # Clear cache
                    st.cache_data.clear()
                    
                    st.success(f"✅ Đã xử lý ngày {next_date.date()}")
                    
                    if role == 'Admin':
                        # Show results only to Admin
                        st.divider()
                        st.subheader("🔥 Top 5 Panic Investors ngày vừa xử lý")
                        
                        df_panic = run_query(engine, """
                            SELECT * FROM BehaviorSignals 
                            WHERE ObservationDate = :d 
                            ORDER BY PanicScore DESC LIMIT 5
                        """, {'d': next_date})
                        
                        if not df_panic.empty:
                            st.dataframe(df_panic, use_container_width=True, hide_index=True)
                        else:
                            st.info("Không có dữ liệu")
                    else:
                        st.info("Kết quả chi tiết sau mô phỏng chỉ hiển thị cho Admin.")
                        
            except Exception as e:
                st.error(f"❌ Lỗi trong quá trình mô phỏng: {str(e)}")
