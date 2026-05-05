class Portfolio:
    def __init__(self, investor_id, initial_cash):
        self.investor_id = investor_id
        self.cash = float(initial_cash)
        self.stock = {}# Số lượng cổ phiếu nắm giữ
        self.avg_price = {} # Giá vốn trung bình (để tính lãi lỗ thực tế nếu cần)

    def execute_buy(self,ticker, quantity, price):
        """
        Thực hiện lệnh MUA
        - Trừ tiền mặt
        - Cộng cổ phiếu
        - Tính lại giá vốn trung bình (Average Price)
        """
        cost = quantity * price
        
        # Check an toàn: Không cho mua âm tiền
        if cost > self.cash:
            return False 

        # Tính giá vốn trung bình mới (Weighted Average)
        # (Giá cũ * Lượng cũ + Giá mới * Lượng mới) / Tổng lượng mới
        current_qty = self.stock.get(ticker,0)
        current_avg = self.avg_price.get(ticker, 0.0)
        new_total_qty = current_qty + quantity
        self.avg_price[ticker] = ((current_qty * current_avg) + (quantity * price)) / new_total_qty

        self.cash -= cost
        self.stock[ticker] = new_total_qty
        return True

    def execute_sell(self,ticker,quantity, price):
        """
        Thực hiện lệnh BÁN
        - Cộng tiền mặt
        - Trừ cổ phiếu
        """
        current_qty = self.stock.get(ticker, 0)
        # Check an toàn: Không cho bán khống (nếu bạn không muốn support short sell)
        if quantity > current_qty:
            return False 

        revenue = quantity * price
        self.cash += revenue
        self.stock[ticker] = current_qty - quantity
        
        # Nếu bán hết sạch thì reset giá vốn về 0 cho gọn
        if self.stock[ticker] == 0:
            self.avg_price[ticker] = 0.0
            
        return True
    def get_avg_price(self, ticker):
        """Lấy giá vốn của một mã cụ thể (Dùng cho Agent tính lãi/lỗ)"""
        return self.avg_price.get(ticker, 0.0)

    def get_stock_quantity(self, ticker):
        """Lấy số lượng đang nắm giữ của một mã cụ thể"""
        return self.stock.get(ticker, 0)
    def get_snapshot(self, current_date, market_prices_dict):
        """
        Chụp ảnh tài sản cuối ngày.
        Output: Dictionary khớp với cột trong bảng Portfolio_History SQL
        """
        total_stock_value = 0.0
        #Duyệt qua tất cả các mã đang có trong túi (Portfolio)
        for ticker, qty in self.stock.items():
            # Lấy giá thị trường tương ứng của mã đó
            current_market_price = market_prices_dict.get(ticker, 0.0)
            total_stock_value += (qty * current_market_price)
        # Tổng tài sản (NAV)
        total_asset = self.cash + total_stock_value
        
        return {
            "TradeDate": current_date,
            "InvestorID": self.investor_id,
            "NAV": round(total_asset, 2),
            "CashBalance": round(self.cash, 2),
            "Stock_Value": round(total_stock_value, 2)
        }