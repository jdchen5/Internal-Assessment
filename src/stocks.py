# stocks.py

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ==== Price Fetching Utilities ====

def fetch_current_price(symbol: str, fallback: float | None = None) -> float | None:
    """
    Return the latest closing price for a symbol.
    Falls back to the provided fallback value if unavailable.
    """
    if not symbol:
        return fallback

    try:
        df = yf.Ticker(symbol).history(period="1d", auto_adjust=True)
        if df.empty:
            return fallback
        return float(df["Close"].iloc[-1])
    except Exception:
        return fallback


def fetch_history(symbol: str, period: str = "1mo") -> pd.DataFrame:
    """
    Return historical OHLC data for a symbol.
    Always returns a DataFrame (empty on error).
    """
    try:
        df = yf.Ticker(symbol).history(period=period, auto_adjust=True)
        return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def fetch_long_history(symbol: str, years: int = 2) -> pd.DataFrame:
    """
    Return long-term historical data.
    years=2 → fetch 2 years of history.
    """
    try:
        df = yf.Ticker(symbol).history(period=f"{years}y", auto_adjust=True)
        return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# ==== Stock-Level Computations ====

def stock_snapshot(stock: dict) -> dict:
    """
    Given a stock dict:
        {
            "symbol": "AAPL",
            "shares": 10,
            "purchase_price": 150,
            "current_price": 165 (optional)
        }

    Returns a consistent snapshot:
        {
            purchase_price,
            current_price,
            purchase_value,
            current_value,
            gain,
            gain_pct
        }
    """

    symbol = stock.get("symbol")
    shares = stock.get("shares", 1)

    purchase_price = stock.get("purchase_price", stock.get("price", 0))

    # Best available current price
    current_price = (
        stock.get("current_price")
        or fetch_current_price(symbol, fallback=purchase_price)
    )

    # Calculations
    purchase_value = purchase_price * shares
    current_value = current_price * shares
    gain = current_value - purchase_value
    gain_pct = (gain / purchase_value * 100) if purchase_value > 0 else 0

    return {
        "purchase_price": float(purchase_price),
        "current_price": float(current_price),
        "purchase_value": float(purchase_value),
        "current_value": float(current_value),
        "gain": float(gain),
        "gain_pct": float(gain_pct),
    }

# ==== Portfolio-Level Computations ====

def portfolio_summary(stocks: list[dict]) -> dict:
    """
    Aggregate summary for an entire portfolio based on stock_snapshot results.

    Returns:
        {
            total_purchase,
            total_current,
            gain,
            gain_pct
        }
    """

    total_purchase = 0.0
    total_current = 0.0

    for s in stocks:
        snap = stock_snapshot(s)
        total_purchase += snap["purchase_value"]
        total_current += snap["current_value"]

    gain = total_current - total_purchase
    gain_pct = (gain / total_purchase * 100) if total_purchase > 0 else 0

    return {
        "total_purchase": total_purchase,
        "total_current": total_current,
        "gain": gain,
        "gain_pct": gain_pct,
    }

# ==== Linear Regression Prediction Utility ====

def linear_prediction(price_series: pd.Series, future_days: int = 365) -> dict | None:
    """
    Perform simple linear regression forecasting future stock price.
    Returns:
        {
            slope,
            intercept,
            current_price,
            predicted_price,
            future_predictions,
            reg_line
        }
    If < 30 days of data, returns None.
    """

    if price_series is None or len(price_series) < 30:
        return None

    # Convert to numpy arrays
    X = np.arange(len(price_series))
    y = price_series.values

    # Fit regression line
    slope, intercept = np.polyfit(X, y, 1)

    # Regression line for historical data
    reg_line = slope * X + intercept

    # Future prediction
    future_X = np.arange(len(price_series), len(price_series) + future_days)
    future_predictions = slope * future_X + intercept

    predicted_price = future_predictions[-1]
    current_price = y[-1]

    # Optional model quality metric
    ss_res = np.sum((y - reg_line) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {
        "slope": slope,
        "intercept": intercept,
        "current_price": float(current_price),
        "predicted_price": float(predicted_price),
        "future_predictions": future_predictions,
        "reg_line": reg_line,
        "r_squared": float(r_squared),
    }
