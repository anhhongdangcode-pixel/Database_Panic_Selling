import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import sys
from pathlib import Path

# Import config from streamlit_app folder
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_CONNECTION_STR

# Role-based connection strings
ROLE_CREDENTIALS = {
    'Admin': {
        'connection_str': DB_CONNECTION_STR
    },
    'Analyst': {
        'user': 'analyst_user',
        'password': 'Analyst@2025'
    },
    'Viewer': {
        'user': 'viewer_user',
        'password': 'Viewer@2025'
    }
}


@st.cache_resource
def get_engine(role):
    """
    Get SQLAlchemy engine for specified role with caching.
    
    Args:
        role (str): 'Admin', 'Analyst', or 'Viewer'
        
    Returns:
        sqlalchemy.engine.Engine: Database engine
    """
    if role == 'Admin':
        connection_str = ROLE_CREDENTIALS['Admin']['connection_str']
    else:
        # Parse base connection string and replace credentials
        creds = ROLE_CREDENTIALS[role]
        base_str = DB_CONNECTION_STR
        
        # Replace user and password in connection string
        # Assuming format: mssql+pyodbc://user:password@driver/database
        import re
        pattern = r'(mssql\+pyodbc:\/\/)([^:]+):([^@]+)@'
        connection_str = re.sub(
            pattern,
            rf'\1{creds["user"]}:{creds["password"]}@',
            base_str
        )
    
    engine = create_engine(connection_str, echo=False)
    return engine


@st.cache_data(ttl=30)
def run_query(_engine, sql, params=None):
    """
    Execute SQL query with caching (30 seconds TTL).
    
    Args:
        _engine: SQLAlchemy engine (prefixed with _ to skip caching)
        sql (str): SQL query string
        params (dict): Query parameters
        
    Returns:
        pd.DataFrame: Query result or empty DataFrame if error
    """
    try:
        if params:
            result = pd.read_sql(text(sql), _engine, params=params)
        else:
            result = pd.read_sql(text(sql), _engine)
        return result
    except Exception as e:
        st.error(f"❌ Lỗi truy vấn: {str(e)}")
        return pd.DataFrame()


def test_connection(engine):
    """
    Test database connection.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
