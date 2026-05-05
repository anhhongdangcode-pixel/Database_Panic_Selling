# 📉 Panic Selling Detection - Streamlit App

Ứng dụng Streamlit cho việc phát hiện và phân tích hành vi bán tháo của nhà đầu tư trên thị trường chứng khoán.

## 🚀 Cài đặt & Chạy

### 1. Cài đặt Dependencies

```bash
pip install -r requirements.txt
```

### 2. Chạy Ứng dụng

```bash
streamlit run app.py
```

Ứng dụng sẽ mở tại `http://localhost:8501`

## 📋 Cấu trúc Ứng dụng

```
streamlit_app/
├── app.py                 # Main application entry point
├── requirements.txt       # Python dependencies
├── pages/
│   ├── __init__.py
│   ├── dashboard.py       # Overview dashboard
│   ├── investors.py       # Investor management (Admin only)
│   ├── market.py          # Market data & analysis (Admin only)
│   ├── analytics.py       # Behavioral analytics (Admin/Analyst)
│   └── next_day.py        # Next day simulation (Admin/Analyst)
└── utils/
    ├── __init__.py
    ├── db.py              # Database connection & queries
    └── charts.py          # Chart styling helpers
```

## 👥 Vai trò & Quyền hạn

### Admin (🔴)
- Truy cập **tất cả** trang
- Quản lý nhà đầu tư
- Xem dữ liệu thị trường chi tiết
- Chạy mô phỏng ngày tiếp theo

**Thông tin đăng nhập:**
- Sử dụng connection string gốc từ `config.py`

### Analyst (🟠)
- Dashboard
- Phân tích hành vi
- Mô phỏng ngày tiếp theo

**Thông tin đăng nhập:**
- User: `analyst_user`
- Password: `Analyst@2025`

### Viewer (🟢)
- Chỉ xem Dashboard
- Không thấy InvestorID

**Thông tin đăng nhập:**
- User: `viewer_user`
- Password: `Viewer@2025`

## 📊 Các Trang Chính

### 1. Dashboard 📊
- **Metrics:** Tổng investors, warnings hôm nay, high panic count, ngày mới nhất
- **Charts:**
  - Pie chart: Phân bố Risk Profile
  - Bar chart: Panic Level hôm nay
  - Line chart: NAV theo Risk Profile
  - Top 10 nhà đầu tư có PanicScore cao

### 2. Investors 👥 (Admin only)
- Bộ lọc: Tìm kiếm ID/Tên, Risk Profile, Min Panic Score
- Chi tiết nhà đầu tư:
  - NAV History
  - Trade History (với màu sắc theo BUY/SELL)
  - PanicScore Timeline

### 3. Market Overview 📈 (Admin only)
- Candlestick chart với:
  - Market Regime nền màu
  - Volume subplot
- Thống kê: Số ngày theo regime, Avg Daily Return

### 4. Behavioral Analytics 📊 (Admin/Analyst)
- Histograms: DrawdownLevel, SellSpike, LossSensitivity
- Scatter plot: Tương quan các signals
- Box plot: PanicScore by RiskProfile
- Timeline: Warning counts
- Chi tiết warnings

### 5. Next Day Simulation 🚀 (Admin/Analyst)
- Status cards: Ngày cuối, Còn bao nhiêu ngày, Tổng ngày
- Nút simulate: Chạy mô phỏng ngày tiếp theo
- Hiển thị top 5 panic investors ngày mới

## 🔧 Cấu hình

### Database Connection
- Chỉnh sửa `config.py` trong thư mục `src/` để thay đổi connection string
- Format: `mssql+pyodbc://username:password@driver/database`

### Các View cần thiết
Ứng dụng yêu cầu các view sau trong database:
- `vw_investor_panic_latest`
- `vw_daily_panic_summary`
- `vw_nav_by_riskprofile`
- `vw_investor_trade_history`
- `vw_warning_dashboard`

## 💾 Cache & Performance

- **Database connections:** Cached bằng `@st.cache_resource` (không expire)
- **Queries:** Cached bằng `@st.cache_data(ttl=30)` (30 giây)
- Nút "Clear Cache" tự động trong `Next Day Simulation` sau khi update

## ⚠️ Xử lý Lỗi

- Tất cả query có try/except, trả về empty DataFrame nếu lỗi
- Hiển thị warning/error messages cho user
- Role-based access control tự động ẩn trang không được phép

## 📝 Ghi chú Kỹ thuật

- Tất cả query dùng **parameterized** (không SQL injection)
- Mỗi page là hàm `render(engine, role)` độc lập
- Routing 100% qua `session_state` trong `app.py`
- Plotly charts với `use_container_width=True`
- Python 3.8+

## 🐛 Troubleshooting

### Lỗi import `config`
- Đảm bảo `src/config.py` tồn tại
- Check `sys.path` trong `utils/db.py`

### Lỗi connection database
- Verify connection string trong `config.py`
- Check ODBC driver là ODBC Driver 17 for SQL Server
- Verify database user credentials

### Lỗi query
- Check xem các view có tồn tại không
- Verify role có quyền truy cập view
- Xem logs trong database

### Streamlit slow/lag
- Clear cache: `st.cache_data.clear()`
- Reduce TTL cache từ 30 giây
- Optimize queries
