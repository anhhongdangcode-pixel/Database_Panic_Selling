SET FOREIGN_KEY_CHECKS = 0;

DROP DATABASE IF EXISTS panic_selling_project; -- Đổi tên DB cho đúng ngữ cảnh
CREATE DATABASE panic_selling_project;
USE panic_selling_project;

-- 1. Bảng MarketData (Đổi từ Market_Data)
-- Yêu cầu: MarketID, TradeDate, Ticker, ClosePrice, DailyReturn, Volatility
CREATE TABLE MarketData (
    MarketID INT AUTO_INCREMENT PRIMARY KEY, -- Thêm MarketID theo chuẩn yêu cầu
    TradeDate DATE,                          -- Đổi Date -> TradeDate
    Ticker VARCHAR(10),
    Open DECIMAL(15,2),  
    High DECIMAL(15,2),
    Low DECIMAL(15,2),
    ClosePrice DECIMAL(15,2),                -- Đổi Close -> ClosePrice
    Volume BIGINT,   
    DailyReturn FLOAT,                       -- Đổi Percent_Change -> DailyReturn
    Volatility FLOAT,                        -- Thêm cột Volatility theo yêu cầu

    Market_Regime VARCHAR(50),               
    -- Giữ lại các technical indicators của bạn để phục vụ sinh data:
    MA_Volume_30 FLOAT, 
    RSI_14 FLOAT,
    MA_20 FLOAT,
    UNIQUE INDEX idx_market_date_ticker (TradeDate, Ticker) -- Index phụ để query nhanh
);

-- 2. Bảng Investors
-- Yêu cầu: InvestorID, InvestorName, RiskProfile, JoinDate
CREATE TABLE Investors (
    InvestorID VARCHAR(20) PRIMARY KEY,      -- Bỏ dấu gạch dưới để khớp tên yêu cầu
    InvestorName VARCHAR(100),               -- Đổi Name -> InvestorName
    RiskProfile VARCHAR(20),                 -- Đổi Investor_Type -> RiskProfile (chứa 'FOMO', 'RATIONAL', 'NOISE')
    JoinDate DATE,                           -- Thêm JoinDate theo yêu cầu
    
    -- Giữ nguyên các tham số tâm lý làm lõi tạo data của bạn:
    Chasing_Bias FLOAT,           
    Loss_Aversion FLOAT,          
    Risk_Appetite FLOAT,         
    Impatience FLOAT,             
    Initial_Balance DECIMAL(15,2)
);

-- 3. Bảng Trades (Đổi từ Transactions)
-- Yêu cầu: TradeID, InvestorID, Ticker, TradeDate, TradeType, Quantity, Price, TradeValue
CREATE TABLE Trades (
    TradeID VARCHAR(20) PRIMARY KEY,         -- Đã thêm PRIMARY KEY như bạn lưu ý
    InvestorID VARCHAR(20),
    Ticker VARCHAR(10),
    TradeDate DATE,                          -- Đổi Date -> TradeDate
    TradeType VARCHAR(10),                   -- Đổi Action -> TradeType ('BUY', 'SELL')
    Quantity INT,
    Price DECIMAL(15,2),      
    TradeValue DECIMAL(15,2),                -- Thêm TradeValue = Quantity * Price
    
    -- Giữ lại các cột tracking logic sinh data của bạn:
    Return_Pct FLOAT, 
    Reason VARCHAR(50),                      -- Quan trọng: Nhãn hành vi (PANIC_SELL, etc.)
    
    FOREIGN KEY (InvestorID) REFERENCES Investors(InvestorID)
);

-- 4. Bảng Portfolios (Gộp từ Portfolios và Portfolio_History cũ)
-- Yêu cầu: PortfolioID, InvestorID, TradeDate, NAV, CashBalance[cite: 1]
-- Lưu ý: Đề bài muốn lưu lịch sử NAV theo ngày, nên bảng này có bản chất giống Portfolio_History cũ của bạn
CREATE TABLE Portfolios (
    PortfolioID INT AUTO_INCREMENT PRIMARY KEY, -- Thêm PK mới
    InvestorID VARCHAR(20),
    TradeDate DATE,                             -- Đổi Date -> TradeDate
    NAV DECIMAL(15,2),                          -- Đổi Total_Asset -> NAV (Net Asset Value)
    CashBalance DECIMAL(15,2),                  -- Đổi Cash_Balance -> CashBalance
    
    -- Bạn có thể giữ lại Stock_Value nếu cần cho logic tính toán
    Stock_Value DECIMAL(15,2),    
    
    INDEX idx_portfolio_date (TradeDate),
    FOREIGN KEY (InvestorID) REFERENCES Investors(InvestorID)
);

-- 5. Bảng BehaviorSignals (Đổi và nâng cấp từ Fomo_Scores)
-- Yêu cầu: SignalID, InvestorID, ObservationDate, DrawdownLevel, SellSpike, LossSensitivity, PanicScore[cite: 1]
CREATE TABLE BehaviorSignals (
    SignalID INT AUTO_INCREMENT PRIMARY KEY, -- Đổi Result_ID -> SignalID
    InvestorID VARCHAR(20),
    ObservationDate DATE,                    -- Đổi Score_Date -> ObservationDate
    
    -- 3 Core Signals thay vì Fomo_Score chung chung:
    DrawdownLevel FLOAT,
    SellSpike FLOAT,
    LossSensitivity FLOAT,
    
    PanicScore FLOAT,                        -- Điểm tổng hợp cuối cùng
    
    FOREIGN KEY (InvestorID) REFERENCES Investors(InvestorID)
);

-- 6. Bảng Warnings (BẢNG MỚI HOÀN TOÀN)
-- Yêu cầu: WarningID, InvestorID, WarningDate, PanicLevel, Confidence, KeySignals[cite: 1]
CREATE TABLE Warnings (
    WarningID INT AUTO_INCREMENT PRIMARY KEY,
    InvestorID VARCHAR(20),
    WarningDate DATE,
    PanicLevel VARCHAR(20),                  -- 'Low', 'Medium', 'High'[cite: 1]
    Confidence FLOAT,                        -- Độ tin cậy của cảnh báo[cite: 1]
    KeySignals TEXT,                         -- Ví dụ: '["sell_spike", "drawdown_sensitivity"]'[cite: 1]
    
    FOREIGN KEY (InvestorID) REFERENCES Investors(InvestorID)
);

SET FOREIGN_KEY_CHECKS = 1;