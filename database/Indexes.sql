USE panic_selling_project;

-- =========================================================
-- 1. INDEXES CHO BẢNG TRADES
-- =========================================================
CREATE INDEX idx_trades_investor ON Trades(InvestorID);
CREATE INDEX idx_trades_date ON Trades(TradeDate);
CREATE INDEX idx_trades_investor_date ON Trades(InvestorID, TradeDate);
CREATE INDEX idx_trades_ticker ON Trades(Ticker);
CREATE INDEX idx_trades_reason ON Trades(Reason);

-- =========================================================
-- 2. INDEXES CHO BẢNG PORTFOLIOS
-- =========================================================
CREATE INDEX idx_portfolios_investor ON Portfolios(InvestorID);
CREATE INDEX idx_portfolios_investor_date ON Portfolios(InvestorID, TradeDate);

-- =========================================================
-- 3. INDEXES CHO BẢNG BEHAVIORSIGNALS
-- =========================================================
CREATE INDEX idx_behavior_investor ON BehaviorSignals(InvestorID);
CREATE INDEX idx_behavior_date ON BehaviorSignals(ObservationDate);
CREATE INDEX idx_behavior_investor_date ON BehaviorSignals(InvestorID, ObservationDate);

-- =========================================================
-- 4. INDEXES CHO BẢNG WARNINGS
-- =========================================================
CREATE INDEX idx_warnings_investor ON Warnings(InvestorID);
CREATE INDEX idx_warnings_date ON Warnings(WarningDate);
CREATE INDEX idx_warnings_level ON Warnings(PanicLevel);

-- =========================================================
-- 5. INDEXES CHO BẢNG INVESTORS
-- =========================================================
CREATE INDEX idx_investors_profile ON Investors(RiskProfile);

-- MarketData đã có UNIQUE INDEX (TradeDate, Ticker) từ lúc khởi tạo.