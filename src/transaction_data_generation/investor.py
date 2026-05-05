import sys
import os
import random
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from portfolio import Portfolio

class InvestorAgent:
    def __init__(self, row_data):
        self.id = row_data.get('InvestorID', row_data.get('Investor_ID'))
        self.type = row_data.get('RiskProfile', row_data.get('Investor_Type')) 
        
        # --- 4 BIẾN TÂM LÝ ---
        self.chasing_bias = float(row_data.get('Chasing_Bias', 0.5))
        self.loss_aversion = float(row_data.get('Loss_Aversion', 0.5))
        self.risk_appetite = float(row_data.get('Risk_Appetite', 0.5))
        self.impatience = float(row_data.get('Impatience', 0.5))
        
        # --- MỤC TIÊU LỢI NHUẬN ---
        # Rational: Target 15% - 25%
        # FOMO: None (Đánh theo cảm xúc)
        if self.type == 'RATIONAL':
            self.target_profit_pct = random.uniform(0.15, 0.25) 
            self.stop_loss_pct = random.uniform(-0.07, -0.10)
        else:
            self.target_profit_pct = None
            self.stop_loss_pct = None 

        # Kết nối ví
        initial_cash = float(row_data['Initial_Balance'])
        self.portfolio = Portfolio(self.id, initial_cash)

    def check_wake_up(self, ticker, market_info):
            """
            [LOGIC MỚI - FULL 4 CASES] 
            Sự chú ý dựa trên từng mã (Per-Stock Attention).
            Bao phủ toàn bộ 4 trạng thái thị trường để tạo Noise tự nhiên.
            """
            specific_regime = market_info['Market_Regime']
            price = market_info['Close']
            
            # 1. Kiểm tra xem có đang cầm ĐÚNG MÃ NÀY không?
            qty = self.portfolio.get_stock_quantity(ticker)
            has_position = qty > 0
            
            prob = 0.05 # Base probability

            # ---------------------------------------------------------
            # TRƯỜNG HỢP A: ĐANG CẦM HÀNG (ticker này) -> Tâm lý "Giữ của"
            # ---------------------------------------------------------
            if has_position:
                # --- 1. AUTO-TRIGGER (Giữ nguyên logic cũ) ---
                avg_price = self.portfolio.get_avg_price(ticker)
                if avg_price > 0:
                    current_return = (price - avg_price) / avg_price
                else:
                    current_return = 0.0
                
                if self.type == 'RATIONAL':
                    if current_return <= self.stop_loss_pct: return True
                    if self.target_profit_pct and current_return >= self.target_profit_pct: return True
                else: # FOMO
                    if abs(current_return) > 0.07: return True

                # --- 2. REGIME ATTENTION (Full 4 Cases) ---
                if self.type == 'RATIONAL':
                    if specific_regime == 'PANIC':                prob = 0.95 # Quản trị rủi ro chặt
                    elif specific_regime == 'SIDEWAY_DISTRIBUTION': prob = 0.80 # Cảnh giác cao
                    elif specific_regime == 'EXPLOSION':          prob = 0.50 # Check để chốt lời chủ động
                    elif specific_regime == 'SIDEWAY_ACCUMULATION': prob = 0.20 # Check ít, kiên nhẫn nắm giữ
                    
                else: # FOMO
                    if specific_regime == 'EXPLOSION':            prob = 0.95 # Sướng quá vào xem liên tục
                    elif specific_regime == 'PANIC':              prob = 0.90 # Hoảng loạn vào xem liên tục
                    elif specific_regime == 'SIDEWAY_DISTRIBUTION': prob = 0.60 # Lo lắng, check nhiều
                    elif specific_regime == 'SIDEWAY_ACCUMULATION': prob = 0.15 # Chán, nhưng vẫn vào xem (Noise)

            # ---------------------------------------------------------
            # TRƯỜNG HỢP B: ĐANG CẦM TIỀN (với mã này) -> Tâm lý "Săn hàng"
            # ---------------------------------------------------------
            else:
                if self.type == 'RATIONAL':
                    # Rational săn hàng giá trị
                    if specific_regime == 'SIDEWAY_ACCUMULATION':   prob = 0.40 # Vùng mua ưa thích
                    elif specific_regime == 'PANIC':                prob = 0.50 # Canh bắt đáy giá trị
                    elif specific_regime == 'SIDEWAY_DISTRIBUTION': prob = 0.05 # Tránh xa (nhưng vẫn có 5% ngó nghiêng)
                    elif specific_regime == 'EXPLOSION':            prob = 0.10 # Ít khi Fomo, nhưng vẫn có 10% tò mò
                
                else: # FOMO
                    # FOMO bị hút bởi sự ồn ào
                    if specific_regime == 'EXPLOSION':              prob = 0.95 # Sợ lỡ tàu -> Vào xem ngay
                    elif specific_regime == 'SIDEWAY_DISTRIBUTION': prob = 0.60 # Tưởng ngon -> Vào xem
                    elif specific_regime == 'PANIC':                prob = 0.20 # Sợ bắt dao rơi (nhưng vẫn có 20% liều)
                    elif specific_regime == 'SIDEWAY_ACCUMULATION': prob = 0.10 # Buồn chán, vào xem cầu may (Noise)

            # Cộng thêm tính cách cá nhân
            prob += (self.impatience * 0.05)
            
            return random.random() < min(1.0, prob)

    def decide_action(self,ticker, market_info):
        """[STEP 2] Logic Ra Quyết Định (Entry & Exit)"""
        price = market_info['Close']
        regime = market_info['Market_Regime']
        date = market_info['Date']
        
        avg_price = self.portfolio.get_avg_price(ticker)
        current_stock_qty = self.portfolio.get_stock_quantity(ticker)

        current_return = 0.0
        if current_stock_qty > 0 and avg_price > 0:
            current_return = (price - avg_price) / avg_price
        
        action = 'HOLD' 
        
        # ==========================================
        # 1. LOGIC CHO RATIONAL
        # ==========================================
        if self.type == 'RATIONAL':
            if current_stock_qty > 0:
                if current_return <= self.stop_loss_pct: action = 'SELL'
                elif self.target_profit_pct and current_return >= self.target_profit_pct: action = 'SELL'
                elif action == "HOLD":
                    if regime == 'SIDEWAY_ACCUMULATION' or regime == 'SIDEWAY_NOISE':
                        if random.random() < (self.impatience * 0.5): 
                            action = 'SELL'
                    
                    elif regime == 'EXPLOSION':
                        # Priority 2: Lãi quá lớn
                        if current_return > 0.30:
                            if random.random() < 0.7:
                                action = 'SELL'
                        
                        # Priority 3: Sợ mất lãi
                        elif current_return > 0.10:
                            if random.random() < (self.loss_aversion * 1.5):
                                action = 'SELL'
                    
                    elif regime == 'SIDEWAY_DISTRIBUTION':
                        if random.random() < self.loss_aversion:
                            action = 'SELL'
                
                    elif regime == 'PANIC':
                        if random.random() < self.loss_aversion:
                            action = 'SELL'        
            
            if action == "HOLD":
                if regime == 'SIDEWAY_ACCUMULATION' or regime == 'SIDEWAY_NOISE':
                    if random.random() < self.risk_appetite: 
                        action = 'BUY'
                
                elif regime == 'EXPLOSION':
                    # RATIONAL rất hiếm khi mua đuổi
                    if random.random() < (self.chasing_bias * 0.1):
                        action = 'BUY'
                
                elif regime == 'SIDEWAY_DISTRIBUTION':
                    trap_prob = (self.risk_appetite + self.chasing_bias) / 2
                    if random.random() < (trap_prob * 0.3):  
                        action = 'BUY'
                
                elif regime == 'PANIC':
                    # Bắt đáy thận trọng
                    catching_prob = self.risk_appetite * 0.4
                    if random.random() < catching_prob:
                        action = 'BUY'
                        
                        
        # ==========================================
        # 2. LOGIC CHO FOMO
        # ==========================================
        elif self.type == 'FOMO':

            # --- BÁN (Exit) ---
            if current_stock_qty > 0:
                
                    
                if action == "HOLD":    
                    if regime == 'SIDEWAY_ACCUMULATION' or regime == 'SIDEWAY_NOISE':
                        if random.random() < (self.impatience * 0.7): action = 'SELL' # Bán vì chán
                        elif current_return > 0: # Bán vì ăn non
                            thresh = max(0.01, 0.08 - (self.impatience * 0.08))
                            if current_return > thresh and random.random() < self.impatience:
                                action = 'SELL'
                    
                    elif regime == 'EXPLOSION':
                        if current_return > 0:
                            # [FIX]: Hạ thấp ngưỡng Greed xuống để FOMO bán sớm hơn (Ăn non)
                            # Impatience cao (0.9) -> Threshold thấp (0.02 - 2%).
                            # Impatience thấp (0.1) -> Threshold cao (0.10 - 10%).
                            impatience_threshold = max(0.01, 0.11 - (self.impatience * 0.10))
                            
                            if current_return > impatience_threshold:
                                # Đã vượt ngưỡng chịu đựng -> Bán
                                if random.random() < self.impatience:
                                    action = 'SELL'
                    
                    # CASE 7: Distribution (Gồng lỗ/Kẹp hàng - Logic 2-Stage của bạn)
                    elif regime == 'SIDEWAY_DISTRIBUTION':
                        if current_return < 0: # Đang LỖ
                            # Ngưỡng sợ hãi: Lỗ -8% đến -13%
                            fear_threshold = -0.05 - (self.loss_aversion * 0.08)
                            
                            if current_return < fear_threshold:
                                # Stage 2: Sợ quá bán tháo (Panic Sell)
                                # Loss Aversion càng cao càng DỄ bán khi vượt ngưỡng chịu đựng
                                panic_prob = 1.0 - (self.loss_aversion * 0.5)
                                if random.random() < panic_prob: action = 'SELL'
                            else:
                                # Lỗ nhẹ -> Gồng (Ostrich Effect)
                                # Loss Aversion cao -> Khó bán -> Gồng
                                if random.random() > (self.loss_aversion * 1.2): action = 'SELL'
                        
                        else: # Đang LÃI (Bull trap)
                            # Chốt lãi vội vàng
                            if random.random() < (self.impatience * 0.7): action = 'SELL'

                # CASE 8: Panic (Đầu hàng - Logic 2-Stage của bạn)
                    elif regime == 'PANIC':
                        if current_return < 0: # Đang LỖ
                            # Stage 1: Ngưỡng đầu hàng (Capitulation)
                            # Vẫn giữ logic cũ của bạn (Rất tốt)
                            capitulation_threshold = -0.15 - (self.loss_aversion * 0.10)
                            
                            if current_return < capitulation_threshold:
                                # Stage 2: Vỡ trận (Capitulation)
                                # [FIX]: Thay vì cứng 0.9, ta dùng Loss Aversion để điều chỉnh.
                                # Người Loss Aversion càng cao (0.9) càng lì đòn, khó bán hơn chút xíu.
                                # Công thức: 1.0 - (Độ lì * 0.15)
                                # Ví dụ: Lì (0.9) -> Prob bán = 0.865
                                #        Nhát (0.1) -> Prob bán = 0.985 (Bán khẩn cấp)
                                cut_loss_prob = 1.0 - (self.loss_aversion * 0.15)
                                
                                if random.random() < cut_loss_prob: 
                                    action = 'SELL'
                            else:
                                # Lỗ chưa thấm -> Vẫn cố gồng hoặc sợ quá không dám nhìn
                                if random.random() > self.loss_aversion: 
                                    action = 'SELL'
                        
                        else: # Đang LÃI (Hiếm gặp trong Panic)
                            # [FIX]: Thay vì cứng 0.8.
                            # Logic: Trong Panic, người có Loss Aversion càng cao càng SỢ MẤT LÃI (Disposition Effect).
                            # -> Họ sẽ là người bán sớm nhất.
                            # Công thức: Base 0.5 + (Sợ mất lãi * 0.4)
                            # Ví dụ: Sợ (0.9) -> Bán 86%.
                            #        Bình tĩnh (0.1) -> Bán 54% (Có thể giữ chờ hồi).
                            secure_profit_prob = 0.5 + (self.loss_aversion * 0.4)
                            
                            if random.random() < secure_profit_prob: 
                                action = 'SELL'
                         
            if action == "HOLD":
                if regime == 'EXPLOSION':
                    if random.random() < self.chasing_bias: action = 'BUY'
                elif regime == 'SIDEWAY_DISTRIBUTION':
                    if random.random() < self.chasing_bias: action = 'BUY'
                elif regime == 'SIDEWAY_ACCUMULATION' or regime == 'SIDEWAY_NOISE':
                    # Noise mua ngẫu nhiên thấp
                    random_buy = (self.risk_appetite + self.impatience) / 2 * 0.2
                    if random.random() < random_buy: action = 'BUY'
                elif regime == 'PANIC':
                    if random.random() < (self.chasing_bias * 0.4): action = 'BUY'         
        if action == 'HOLD': return None

        # ==========================================
        # 3. LOGIC KHỐI LƯỢNG (SIZING)
        # ==========================================
        quantity = 0
        
        if action == 'BUY':
            max_qty = int(self.portfolio.cash // price)
            if max_qty == 0: return None
            
            # [BUY] Risk Appetite quyết định độ "máu" khi xuống tiền
            # Risk=0.8 -> Mua ~80% tiền. Risk=0.2 -> Mua ~20% tiền.
            # Thêm noise ngẫu nhiên (+/- 10%) để không bị cứng nhắc
            base_pct = self.risk_appetite
            pct = random.uniform(max(0.1, base_pct - 0.1), min(1.0, base_pct + 0.1))
            quantity = int(max_qty * pct)
            
        elif action == 'SELL':
            if current_stock_qty == 0: return None
            
            pct = 1.0 # Mặc định
            
            # --- FOMO: Bán theo độ "Nóng vội" (Impatience) ---
            if self.type == 'FOMO':
                # Thay vì luôn bán 100%, ta để Impatience quyết định
                # Impatience=0.9 (Rất vội) -> Base 95% -> Bán gần như hết sạch (95-100%)
                # Impatience=0.5 (Vừa phải) -> Base 75% -> Có thể giữ lại 1 ít (75-100%)
                base_sell = 0.5 + (self.impatience * 0.5)
                pct = random.uniform(base_sell, 1.0)
                
            # --- RATIONAL: Bán theo Chiến lược & Tính cách ---
            else:
                if regime == 'PANIC':
                    # Cắt lỗ/Quản trị rủi ro:
                    # Càng sợ lỗ (Loss Aversion cao) -> Càng bán nhiều để an tâm
                    # Aversion=0.8 -> Bán từ 74% - 100%
                    base_sell = 0.5 + (self.loss_aversion * 0.3)
                    pct = random.uniform(base_sell, 1.0)
                    
                elif regime == 'EXPLOSION':
                    # Chốt lời từng phần (Scaling Out):
                    # Người "Liều" (Risk cao) -> Bán ít (để lãi chạy tiếp)
                    # Người "An toàn" (Risk thấp) -> Bán nhiều (để chắc ăn)
                    
                    # Risk=0.8 (Liều) -> Safe_factor=0.2 -> Bán tầm 20%-40% (Giữ lại nhiều)
                    # Risk=0.2 (Nhát) -> Safe_factor=0.8 -> Bán tầm 50%-80% (Chốt lời mạnh)
                    safe_factor = 1.0 - self.risk_appetite 
                    min_sell = 0.2 + (safe_factor * 0.3) # Min 0.2 - 0.5
                    max_sell = min_sell + 0.3            # Max 0.5 - 0.8
                    pct = random.uniform(min_sell, max_sell)
                    
                elif regime == 'SIDEWAY_DISTRIBUTION':
                    # Phòng thủ vùng đỉnh:
                    # Tùy độ sợ hãi mà giảm tỷ trọng nhiều hay ít
                    pct = random.uniform(0.3, 0.3 + (self.loss_aversion * 0.5))
                    
                else: 
                    # Accumulation: Cơ cấu danh mục nhẹ nhàng
                    pct = random.uniform(0.1, 0.4)

            # [SAFEGUARD] Đảm bảo pct luôn hợp lệ (10% -> 100%)
            pct = max(0.1, min(1.0, pct))
            quantity = int(current_stock_qty * pct)

        # --- THỰC THI ---
        if quantity <= 0: return None
        
        is_success = False
        if action == 'BUY':
            is_success = self.portfolio.execute_buy(ticker,quantity, price)
        elif action == 'SELL':
            is_success = self.portfolio.execute_sell(ticker,quantity, price)
            
        if is_success:
            return {
                "TradeDate": date,
                "InvestorID": self.id,
                "Ticker": ticker,
                "RiskProfile": self.type,
                "TradeType": action,
                "Price": price,
                "Quantity": quantity,
                "TradeValue": quantity * price,
                "Return_Pct": round(current_return, 4),
                "Reason": f"{regime}_{action}"
            }
            
        return None