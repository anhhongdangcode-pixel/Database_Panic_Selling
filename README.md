# Panic Selling Detection for Individual Investors

**Course:** Introduction to Database Systems — DS66B
**Student:** Le Hong Anh — 11247126
**Repository:** https://github.com/anhhongdangcode-pixel/Database_Panic_Selling

---

## What This Project Does

This project builds a database-backed system that **detects panic selling behavior** among retail investors in the Vietnamese stock market. It simulates 1,000 synthetic investors trading 9 VN tickers over the full year 2025, stores all trading activity in a MySQL database, and provides a Streamlit dashboard to analyze behavioral signals and issue early warnings.

**Panic selling** happens when investors sell their holdings impulsively in response to short-term market drops — often locking in losses unnecessarily. This system tracks signals like sudden sell spikes, high drawdown sensitivity, and elevated panic scores to flag at-risk investors.

---

## Project Structure

```
Database_Panic_Selling/
│
├── data/
│   └── raw/
│       ├── final_market_data_2025.csv        # Pre-prepared market data for 9 VN tickers
│       ├── investors_dummy_data.csv           # Created by investor_data_generation.py
│       ├── simulation_transactions.csv        # Created by simulation.py
│       ├── simulation_portfolio_history.csv   # Created by simulation.py
│       └── behavior_signals.csv              # Created by engineering_feature.py
│
├── database/                                  # All SQL scripts
│   ├── schema.sql                             # 6 tables with primary/foreign keys and constraints
│   ├── indexes.sql                            # 14 indexes for faster queries
│   ├── views.sql                              # 7 analytical views + 1 security view
│   ├── Functions_Procedure.sql                # 4 user-defined functions + 1 stored procedure
│   ├── Trigger.sql                            # Auto-generates warnings after new signals are inserted
│   └── security.sql                           # 3 user roles with different access levels
│
├── src/
│   ├── config.py                              # Database connection settings, file paths, constants
│   ├── data_loader.py                         # (Optional) Fetch market data from vnstock API
│   ├── prepare_market.py                      # Load market CSV into the MarketData table
│   ├── investor_data_generation.py            # Generate 1,000 synthetic investors
│   ├── indicator.py                           # Helper functions for technical indicators
│   ├── investor.py                            # InvestorAgent class — models investor behavior
│   ├── portfolio.py                           # Portfolio class — tracks cash, holdings, and NAV
│   ├── simulation.py                          # Runs the full trading simulation
│   ├── push_to_db.py                          # Loads CSV data into the database (up to Aug 2025)
│   ├── engineering_feature.py                 # Calculates and backfills behavioral signals
│   └── next_day.py                            # Simulates one future trading day at a time
│
├── streamlit_app/
│   ├── app.py                                 # Main app entry point with sidebar navigation
│   ├── pages/
│   │   ├── dashboard.py                       # System overview — key metrics and charts
│   │   ├── investors.py                       # Investor search and detail view (Admin only)
│   │   ├── market.py                          # Market overview with candlestick charts (Admin only)
│   │   ├── analytics.py                       # Behavioral signal analysis — scatter, histogram
│   │   └── next_day.py                        # UI to trigger the next-day simulation
│   └── utils/
│       ├── db.py                              # Role-based database connection helper
│       └── charts.py                          # Shared chart functions
│
├── .env                                       # Database credentials (not committed to Git)
├── .gitignore
└── README.md
```

---

## Setup

### Step 1 — Configure your database credentials

Create a `.env` file in the project root with the following content:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=panic_selling_project
```

### Step 2 — Initialize the database

Open MySQL Workbench and run the SQL scripts **in this exact order**:

```
1. database/schema.sql
2. database/indexes.sql
3. database/views.sql
4. database/Functions_Procedure.sql
5. database/Trigger.sql
6. database/security.sql
```

> Running them out of order will cause errors due to dependencies between scripts.

### Step 3 — Install Python dependencies

```bash
pip install pandas sqlalchemy pymysql faker tqdm streamlit plotly python-dotenv
```

---

## Running the Pipeline

> **Note:** `data/raw/final_market_data_2025.csv` is already included — you do **not** need to run `data_loader.py`. Start directly from Step 1 below.

### Step 1 — Load market data into the database

```bash
cd src
python prepare_market.py
```

Reads the market CSV, calculates volatility for each ticker, and inserts all 2,160 rows into the `MarketData` table.

---

### Step 2 — Generate synthetic investors

```bash
python investor_data_generation.py
```

Creates 1,000 fake investors across three behavioral types — **FOMO**, **RATIONAL**, and **NOISE** — and inserts them into the `Investors` table.

---

### Step 3 — Run the trading simulation

```bash
python simulation.py
```

Simulates all 1,000 investors trading across 9 tickers for the entire year 2025. This produces two CSV files:
- `simulation_transactions.csv`
- `simulation_portfolio_history.csv`

> ⚠️ This step may take a few minutes to complete.

---

### Step 4 — Push historical data to the database

```bash
python push_to_db.py
```

Loads all trade and portfolio data up to **August 31, 2025** into the database. Data from September to December 2025 is intentionally kept in CSV files — it serves as "future" data for the next-day simulation feature.

---

### Step 5 — Backfill behavioral signals

```bash
python engineering_feature.py
```

Calculates four behavioral indicators for each investor across the historical period:
- **DrawdownLevel** — how much the portfolio has fallen from its peak
- **SellSpike** — unusually high sell activity
- **LossSensitivity** — how strongly the investor reacts to losses
- **PanicScore** — an overall panic risk score

Results are inserted into the `BehaviorSignals` table. The database trigger then automatically populates the `Warnings` table.

---

### Step 6 — Launch the dashboard

```bash
cd streamlit_app
streamlit run app.py
```

Opens the web dashboard. Log in using one of the demo credentials below.

---

### Step 7 — Simulate future trading days (optional, repeatable)

```bash
cd src
python next_day.py
```

Each run pushes exactly **one new trading day** (starting September 1, 2025) into the database, calls the end-of-day stored procedure, and triggers automatic warning generation. Run this script repeatedly to advance the simulation day by day.

---

## Demo Login Credentials

| Role | Username | Password | Access |
|------|----------|----------|--------|
| Admin | `admin_user` | `Admin@2025` | All 5 pages — full access |
| Analyst | `analyst_user` | `Analyst@2025` | 3 pages — can run the EOD process |
| Viewer | `viewer_user` | `Viewer@2025` | Dashboard + masked Warning Board only |

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| Market data pre-prepared as CSV | The vnstock API is unstable — data was pre-fetched and verified to ensure reliability |
| Historical cutoff at August 31, 2025 | Allows the system to demonstrate real-time incremental updates via the next-day simulation |
| ELT architecture | Python is only responsible for moving data; all business logic lives in MySQL (UDFs, stored procedure) |
| Trigger for Warnings | Ensures warnings are always generated, regardless of which script inserts the behavioral signals |
| `SEED_VALUE = 2026` | Makes the synthetic dataset fully reproducible across all environments |
