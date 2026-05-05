USE panic_selling_project;

-- =========================================================
-- VIEW 1: vw_investor_selling_summary
-- Mục đích: Tổng hợp hành vi bán của từng investor
-- =========================================================
CREATE OR REPLACE VIEW vw_investor_selling_summary AS
SELECT 
    i.InvestorID, 
    i.InvestorName, 
    i.RiskProfile,
    COUNT(t.TradeID) AS TotalTrades,
    SUM(CASE WHEN t.TradeType = 'SELL' THEN 1 ELSE 0 END) AS TotalSells,
    SUM(CASE WHEN t.TradeType = 'SELL' AND (t.Reason LIKE '%PANIC%' OR t.Reason LIKE '%DISTRIBUTION%') THEN 1 ELSE 0 END) AS PanicSells,
    COALESCE(
        SUM(CASE WHEN t.TradeType = 'SELL' AND (t.Reason LIKE '%PANIC%' OR t.Reason LIKE '%DISTRIBUTION%') THEN 1 ELSE 0 END) 
        / NULLIF(SUM(CASE WHEN t.TradeType = 'SELL' THEN 1 ELSE 0 END), 0), 
    0) AS PanicSellRatio,
    AVG(CASE WHEN t.TradeType = 'SELL' THEN t.Return_Pct ELSE NULL END) AS AvgReturnOnSell
FROM Investors i
LEFT JOIN Trades t ON i.InvestorID = t.InvestorID
GROUP BY i.InvestorID, i.InvestorName, i.RiskProfile;

-- =========================================================
-- VIEW 2: vw_abnormal_sell_periods
-- Mục đích: Các ngày có hoạt động bán bất thường, kết hợp với market regime
-- =========================================================
CREATE OR REPLACE VIEW vw_abnormal_sell_periods AS
SELECT 
    bs.ObservationDate,
    i.InvestorID, 
    i.InvestorName, 
    i.RiskProfile,
    bs.SellSpike, 
    bs.DrawdownLevel, 
    bs.LossSensitivity, 
    bs.PanicScore,
    md.DailyRegime AS Market_Regime,
    w.PanicLevel
FROM BehaviorSignals bs
JOIN Investors i ON bs.InvestorID = i.InvestorID
LEFT JOIN Warnings w ON bs.InvestorID = w.InvestorID AND bs.ObservationDate = w.WarningDate
LEFT JOIN (
    -- Subquery lấy Regime phổ biến nhất trong ngày bằng cách dùng MAX
    -- (Vì MarketData chia theo Ticker, ta gom nhóm lại theo ngày)
    SELECT TradeDate, MAX(Market_Regime) AS DailyRegime
    FROM MarketData
    GROUP BY TradeDate
) md ON bs.ObservationDate = md.TradeDate
-- ⚠️ LƯU Ý NHỎ: Ở đoạn chat trước ta đã thống nhất hạ ngưỡng PanicScore 
-- để Demo có nhiều data. Tôi tạm để 0.40 theo logic mới nhất nhé!
-- Nếu bạn muốn đổi lại ngưỡng cũ thì sửa 0.40 thành 0.65.
WHERE bs.SellSpike >= 0.40 OR bs.PanicScore >= 0.40;

-- =========================================================
-- VIEW 3: vw_warning_dashboard
-- Mục đích: Dashboard tổng hợp toàn bộ cảnh báo, dùng để báo cáo
-- =========================================================
CREATE OR REPLACE VIEW vw_warning_dashboard AS
SELECT 
    w.WarningID, 
    w.WarningDate, 
    w.PanicLevel, 
    w.Confidence, 
    w.KeySignals,
    i.InvestorID, 
    i.InvestorName, 
    i.RiskProfile,
    bs.DrawdownLevel, 
    bs.SellSpike, 
    bs.LossSensitivity, 
    bs.PanicScore
FROM Warnings w
JOIN Investors i ON w.InvestorID = i.InvestorID
JOIN BehaviorSignals bs ON w.InvestorID = bs.InvestorID AND w.WarningDate = bs.ObservationDate
-- Sắp xếp cảnh báo nguy hiểm nhất lên đầu
ORDER BY w.Confidence DESC, w.WarningDate DESC;