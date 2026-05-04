SET FOREIGN_KEY_CHECKS = 0;

DROP DATABASE IF EXISTS fomo_project;
CREATE DATABASE fomo_project;
USE fomo_project;

-- 1. Bảng Market_Data 
CREATE TABLE Market_Data (
    Date DATE,
    Ticker VARCHAR(10),
    Open DECIMAL(15,2),  
    High DECIMAL(15,2),
    Low DECIMAL(15,2),
    Close DECIMAL(15,2),        
    Volume BIGINT,   
    MA_Volume_30 FLOAT, 
    RSI_14 FLOAT,
    MA_20 FLOAT,
    Percent_Change FLOAT,
    PRIMARY KEY (Date, Ticker)
);

-- 2. Bảng Investors 
CREATE TABLE Investors (
    Investor_ID VARCHAR(20) PRIMARY KEY,
    Name VARCHAR(100),
    Investor_Type VARCHAR(20), -- 'FOMO', 'RATIONAL', 'NOISE'
    
    -- Tâm lý
    Chasing_Bias FLOAT,           
    Loss_Aversion FLOAT,          
    Risk_Appetite FLOAT,         
    Impatience FLOAT,             
    
    -- Tài chính
    Initial_Balance DECIMAL(15,2)
);

-- 3. Bảng Transactions
CREATE TABLE Transactions (
    Trans_ID VARCHAR(20),
    Investor_ID VARCHAR(20),
    Date DATE,        
    Ticker VARCHAR(10),
    Action VARCHAR(10), 
    Price DECIMAL(15,2),      
    Quantity INT,
    Return_Pct FLOAT, 
    Reason VARCHAR(50),   -- QUAN TRỌNG: Nhãn hành vi
    FOREIGN KEY (Investor_ID) REFERENCES Investors(Investor_ID)
);

-- 4. Bảng Portfolios 
CREATE TABLE Portfolios (
    Investor_ID VARCHAR(20),
    Ticker VARCHAR(10),        
    
    Quantity_Held INT DEFAULT 0,      
    Avg_Buy_Price DECIMAL(15,2),      
    
    PRIMARY KEY (Investor_ID, Ticker),
    FOREIGN KEY (Investor_ID) REFERENCES Investors(Investor_ID)
);

-- 5. Bảng Portfolio_History 
CREATE TABLE Portfolio_History (
    Date DATE,                  
    Investor_ID VARCHAR(20),
    Total_Asset DECIMAL(15,2),  
    Cash_Balance DECIMAL(15,2),
    Stock_Value DECIMAL(15,2),    
    PRIMARY KEY (Investor_ID, Date), 
    
    -- Index phụ để query theo ngày cho nhanh (nếu cần vẽ biểu đồ tổng quan thị trường)
    INDEX (Date),
    FOREIGN KEY (Investor_ID) REFERENCES Investors(Investor_ID)
);

-- 6. Bảng Fomo_Scores 
CREATE TABLE Fomo_Scores (
    Result_ID INT AUTO_INCREMENT PRIMARY KEY,
    Investor_ID VARCHAR(20),
    Score_Date DATE,
    Fomo_Score FLOAT,    
    Fomo_Level VARCHAR(20), 
    Key_Signals TEXT,    
    FOREIGN KEY (Investor_ID) REFERENCES Investors(Investor_ID)
);

SET FOREIGN_KEY_CHECKS = 1;