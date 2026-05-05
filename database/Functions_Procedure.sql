USE panic_selling_project;

DROP FUNCTION IF EXISTS fn_rolling_drawdown;
DROP FUNCTION IF EXISTS fn_sell_intensity;
DROP FUNCTION IF EXISTS fn_loss_sensitivity;
DROP FUNCTION IF EXISTS fn_panic_score;
DROP PROCEDURE IF EXISTS sp_daily_eod_process;

DELIMITER $$

-- ==========================================
-- UDF 1: fn_rolling_drawdown
-- ==========================================
CREATE FUNCTION fn_rolling_drawdown(
    p_investor_id VARCHAR(20), 
    p_obs_date DATE, 
    p_window_days INT
) 
RETURNS FLOAT
READS SQL DATA
BEGIN
    DECLARE v_peak_nav DECIMAL(15,2);
    DECLARE v_final_nav DECIMAL(15,2);
    DECLARE v_drawdown FLOAT DEFAULT 0.0;
    
    SELECT MAX(NAV) INTO v_peak_nav 
    FROM Portfolios 
    WHERE InvestorID = p_investor_id 
      AND TradeDate BETWEEN DATE_SUB(p_obs_date, INTERVAL p_window_days DAY) AND p_obs_date;
      
    SELECT NAV INTO v_final_nav 
    FROM Portfolios 
    WHERE InvestorID = p_investor_id 
      AND TradeDate <= p_obs_date
    ORDER BY TradeDate DESC LIMIT 1;
    
    IF v_peak_nav > 0 AND v_final_nav IS NOT NULL THEN
        SET v_drawdown = LEAST(1.0, GREATEST(0.0, ((v_peak_nav - v_final_nav) / v_peak_nav) * 5.0));
    END IF;
    
    RETURN v_drawdown;
END$$

-- ==========================================
-- UDF 2: fn_sell_intensity (SellSpike)
-- ==========================================
CREATE FUNCTION fn_sell_intensity(
    p_investor_id VARCHAR(20), 
    p_obs_date DATE, 
    p_window_days INT
) 
RETURNS FLOAT
READS SQL DATA
BEGIN
    DECLARE v_total_sells INT DEFAULT 0;
    DECLARE v_panic_sells INT DEFAULT 0;
    
    SELECT COUNT(*) INTO v_total_sells
    FROM Trades 
    WHERE InvestorID = p_investor_id 
      AND TradeType = 'SELL'
      AND TradeDate BETWEEN DATE_SUB(p_obs_date, INTERVAL p_window_days DAY) AND p_obs_date;
      
    SELECT COUNT(*) INTO v_panic_sells
    FROM Trades 
    WHERE InvestorID = p_investor_id 
      AND TradeType = 'SELL'
      AND (Reason LIKE '%PANIC%' OR Reason LIKE '%DISTRIBUTION%')
      AND TradeDate BETWEEN DATE_SUB(p_obs_date, INTERVAL p_window_days DAY) AND p_obs_date;
      
    IF v_total_sells > 0 THEN
        RETURN CAST(v_panic_sells AS FLOAT) / v_total_sells;
    END IF;
    
    RETURN 0.0;
END$$

-- ==========================================
-- UDF 3: fn_loss_sensitivity
-- ==========================================
CREATE FUNCTION fn_loss_sensitivity(
    p_investor_id VARCHAR(20), 
    p_obs_date DATE, 
    p_window_days INT
) 
RETURNS FLOAT
READS SQL DATA
BEGIN
    DECLARE v_total_sells INT DEFAULT 0;
    DECLARE v_loss_sells INT DEFAULT 0;
    
    SELECT COUNT(*) INTO v_total_sells
    FROM Trades 
    WHERE InvestorID = p_investor_id 
      AND TradeType = 'SELL'
      AND TradeDate BETWEEN DATE_SUB(p_obs_date, INTERVAL p_window_days DAY) AND p_obs_date;
      
    SELECT COUNT(*) INTO v_loss_sells
    FROM Trades 
    WHERE InvestorID = p_investor_id 
      AND TradeType = 'SELL'
      AND Return_Pct < 0
      AND TradeDate BETWEEN DATE_SUB(p_obs_date, INTERVAL p_window_days DAY) AND p_obs_date;
      
    IF v_total_sells > 0 THEN
        RETURN CAST(v_loss_sells AS FLOAT) / v_total_sells;
    END IF;
    
    RETURN 0.0;
END$$

-- ==========================================
-- UDF 4: fn_panic_score
-- ==========================================
CREATE FUNCTION fn_panic_score(
    p_drawdown FLOAT, 
    p_sell_spike FLOAT, 
    p_loss_sensitivity FLOAT
) 
RETURNS FLOAT
DETERMINISTIC
BEGIN
    RETURN LEAST(1.0, GREATEST(0.0,
        (p_drawdown * 0.4) + (p_sell_spike * 0.4) + (p_loss_sensitivity * 0.2)
    ));
END$$

-- ==========================================
-- STORED PROCEDURE: sp_daily_eod_process
-- ==========================================
CREATE PROCEDURE sp_daily_eod_process(IN p_date DATE)
BEGIN
    DECLARE v_investor_id VARCHAR(20);
    DECLARE v_drawdown FLOAT;
    DECLARE v_sell_spike FLOAT;
    DECLARE v_loss_sensitivity FLOAT;
    DECLARE v_panic_score FLOAT;
    DECLARE done INT DEFAULT 0;
    
    -- Lấy danh sách investors có portfolio snapshot trong ngày p_date
    DECLARE cur CURSOR FOR
        SELECT DISTINCT InvestorID 
        FROM Portfolios 
        WHERE TradeDate = p_date;
        
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;
    
    -- Xóa BehaviorSignals của ngày này để tránh duplicate
    DELETE FROM BehaviorSignals WHERE ObservationDate = p_date;
    
    OPEN cur;
    
    read_loop: LOOP
        FETCH cur INTO v_investor_id;
        IF done THEN LEAVE read_loop; END IF;
        
        -- Gọi 4 hàm tính toán
        SET v_drawdown        = fn_rolling_drawdown(v_investor_id, p_date, 30);
        SET v_sell_spike      = fn_sell_intensity(v_investor_id, p_date, 30);
        SET v_loss_sensitivity = fn_loss_sensitivity(v_investor_id, p_date, 30);
        SET v_panic_score     = fn_panic_score(v_drawdown, v_sell_spike, v_loss_sensitivity);
        
        -- INSERT vào BehaviorSignals -> trigger tự bắn vào Warnings
        INSERT INTO BehaviorSignals 
            (InvestorID, ObservationDate, DrawdownLevel, SellSpike, LossSensitivity, PanicScore)
        VALUES 
            (v_investor_id, p_date, v_drawdown, v_sell_spike, v_loss_sensitivity, v_panic_score);
            
    END LOOP;
    
    CLOSE cur;
    
    SELECT 
        COUNT(*) as TotalSignals,
        SUM(CASE WHEN PanicScore >= 0.6 THEN 1 ELSE 0 END) as HighPanic,
        SUM(CASE WHEN PanicScore >= 0.4 AND PanicScore < 0.6 THEN 1 ELSE 0 END) as MediumPanic
    FROM BehaviorSignals 
    WHERE ObservationDate = p_date;
    
END$$

DELIMITER ;