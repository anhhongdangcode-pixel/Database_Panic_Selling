"""
Color helper functions for Streamlit dataframe styling.
"""


def color_panic_level(val):
    """
    Get background color CSS for PanicLevel column.
    
    Args:
        val (str): 'High', 'Medium', 'Low'
        
    Returns:
        str: CSS background-color
    """
    if val == 'High':
        return 'background-color: rgba(255, 0, 0, 0.3)'  # Red
    elif val == 'Medium':
        return 'background-color: rgba(255, 165, 0, 0.3)'  # Orange
    elif val == 'Low':
        return 'background-color: rgba(0, 128, 0, 0.3)'  # Green
    return ''


def color_panic_score(val):
    """
    Get background color CSS for PanicScore column (float 0.0-1.0).
    
    Args:
        val (float): Panic score between 0 and 1
        
    Returns:
        str: CSS background-color
    """
    try:
        val = float(val)
        if val >= 0.6:
            return 'background-color: rgba(255, 0, 0, 0.3)'  # Red
        elif val >= 0.4:
            return 'background-color: rgba(255, 165, 0, 0.3)'  # Orange
        else:
            return 'background-color: rgba(0, 128, 0, 0.3)'  # Green
    except (TypeError, ValueError):
        return ''


def color_trade_type(val):
    """
    Get background color CSS for TradeType column.
    
    Args:
        val (str): 'BUY' or 'SELL'
        
    Returns:
        str: CSS background-color
    """
    if val == 'BUY':
        return 'background-color: rgba(0, 128, 0, 0.3)'  # Green
    elif val == 'SELL':
        return 'background-color: rgba(255, 0, 0, 0.3)'  # Red
    return ''


def color_reason(val):
    """
    Get background color CSS for Reason column.
    
    Args:
        val (str): Reason string (PANIC, DISTRIBUTION, etc.)
        
    Returns:
        str: CSS background-color
    """
    if val == 'PANIC':
        return 'background-color: rgba(139, 0, 0, 0.4)'  # Dark red
    elif val == 'DISTRIBUTION':
        return 'background-color: rgba(255, 165, 0, 0.3)'  # Orange
    else:
        return 'background-color: rgba(128, 128, 128, 0.2)'  # Gray
