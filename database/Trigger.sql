use panic_selling_project;
DROP TRIGGER IF EXISTS trg_after_behaviorsignal_insert;


DELIMITER $$

CREATE TRIGGER trg_after_behaviorsignal_insert
AFTER INSERT ON BehaviorSignals
FOR EACH ROW
BEGIN
    -- Khai báo biến
    DECLARE v_panic_level VARCHAR(20);
    DECLARE v_key_signals TEXT;
    DECLARE v_signals_list VARCHAR(200);

    -- Chỉ xử lý nếu PanicScore đủ ngưỡng
    IF NEW.PanicScore >= 0.4 THEN

        -- Xác định PanicLevel
        IF NEW.PanicScore >= 0.6 THEN
            SET v_panic_level = 'High';
        ELSE
            SET v_panic_level = 'Medium';
        END IF;

        -- Build KeySignals string
        SET v_signals_list = '';

        IF NEW.DrawdownLevel >= 0.1 THEN
            SET v_signals_list = CONCAT(v_signals_list, '"drawdown_sensitivity", ');
        END IF;

        IF NEW.SellSpike >= 0.4 THEN
            SET v_signals_list = CONCAT(v_signals_list, '"sell_spike", ');
        END IF;

        IF NEW.LossSensitivity >= 0.4 THEN
            SET v_signals_list = CONCAT(v_signals_list, '"rapid_liquidation", ');
        END IF;

        -- Xóa dấu phẩy thừa cuối chuỗi rồi bọc ngoặc vuông
        IF v_signals_list != '' THEN
            SET v_signals_list = LEFT(v_signals_list, LENGTH(v_signals_list) - 2);
        END IF;
        SET v_key_signals = CONCAT('[', v_signals_list, ']');

        -- INSERT vào Warnings
        INSERT INTO Warnings (InvestorID, WarningDate, PanicLevel, Confidence, KeySignals)
        VALUES (
            NEW.InvestorID,
            NEW.ObservationDate,
            v_panic_level,
            NEW.PanicScore,
            v_key_signals
        );

    END IF;
END$$

DELIMITER ;