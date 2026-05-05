import streamlit as st
from utils.db import get_engine, test_connection

# Import all pages
from pages import dashboard, investors, market, analytics, next_day

# Page configuration
st.set_page_config(
    page_title="Panic Selling Detection",
    layout="wide",
    page_icon="📉"
)

# Initialize session state
if 'role' not in st.session_state:
    st.session_state['role'] = 'Viewer'
if 'page' not in st.session_state:
    st.session_state['page'] = 'Dashboard'

# Sidebar
with st.sidebar:
    st.markdown("## 📉 Panic Selling Detection")
    
    # Role selector
    selected_role = st.selectbox(
        "Chọn Role",
        ["Admin", "Analyst", "Viewer"],
        index=["Admin", "Analyst", "Viewer"].index(st.session_state['role'])
    )
    st.session_state['role'] = selected_role
    
    # Role badge
    role_colors = {
        'Admin': '🔴',
        'Analyst': '🟠',
        'Viewer': '🟢'
    }
    st.markdown(f"**Role hiện tại:** {role_colors.get(selected_role, '⚪')} {selected_role}")
    
    st.divider()
    
    # Navigation menu based on role
    menu_options = {
        'Admin': ["Dashboard", "Investors", "Market Overview", "Behavioral Analytics", "Next Day Simulation"],
        'Analyst': ["Dashboard", "Behavioral Analytics", "Next Day Simulation"],
        'Viewer': ["Dashboard"]
    }
    
    pages = menu_options.get(st.session_state['role'], ["Dashboard"])
    
    st.markdown("### 📋 Menu")
    selected_page = st.radio(
        "Chọn trang",
        pages,
        index=pages.index(st.session_state['page']) if st.session_state['page'] in pages else 0,
        label_visibility="collapsed"
    )
    st.session_state['page'] = selected_page
    
    st.divider()
    
    # Connection status
    st.markdown("### 🔌 Trạng thái kết nối")
    try:
        engine = get_engine(st.session_state['role'])
        is_connected = test_connection(engine)
        
        if is_connected:
            st.success("🟢 Kết nối thành công", icon="✅")
        else:
            st.error("🔴 Kết nối thất bại", icon="❌")
    except Exception as e:
        st.error(f"🔴 Lỗi: {str(e)}", icon="❌")

# Main content area
try:
    engine = get_engine(st.session_state['role'])
    role = st.session_state['role']
    
    if st.session_state['page'] == 'Dashboard':
        dashboard.render(engine, role)
    elif st.session_state['page'] == 'Investors':
        investors.render(engine, role)
    elif st.session_state['page'] == 'Market Overview':
        market.render(engine, role)
    elif st.session_state['page'] == 'Behavioral Analytics':
        analytics.render(engine, role)
    elif st.session_state['page'] == 'Next Day Simulation':
        next_day.render(engine, role)
    else:
        st.error("Trang không tìm thấy")
        
except Exception as e:
    st.error(f"❌ Lỗi: {str(e)}")
