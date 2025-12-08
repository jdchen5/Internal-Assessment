import streamlit as st
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import time
from urllib.parse import quote
from login import (
    get_user_portfolios, get_all_portfolios, get_portfolio_by_id,
    create_portfolio, update_portfolio, delete_portfolio,
    add_stock_to_portfolio, remove_stock_from_portfolio
)

def handle_logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.page = "login"
    st.rerun()

def calculate_stock_prediction(price_data, future_days=365):
    if len(price_data) < 30:
        return None

    X = np.arange(len(price_data)).reshape(-1, 1)
    y = price_data.values

    coefficients = np.polyfit(X.flatten(), y, 1)
    slope = coefficients[0]
    intercept = coefficients[1]

    y_pred = slope * X.flatten() + intercept

    future_X = np.arange(len(price_data), len(price_data) + future_days)
    future_predictions = slope * future_X + intercept

    residuals = y - y_pred
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {
        'slope': slope,
        'intercept': intercept,
        'predicted_price': future_predictions[-1],
        'y_pred': y_pred,
        'future_predictions': future_predictions,
        'future_X': future_X,
        'r_squared': r_squared,
        'current_price': price_data.iloc[-1]
    }

def calculate_portfolio_value(stocks):
    total_value = 0
    for stock in stocks:
        purchase_price = stock.get('purchase_price', stock.get('price', 0))
        shares = stock.get('shares', 1)
        total_value += purchase_price * shares
    return total_value

def format_percentage_with_color(percentage):
    if percentage > 0:
        return f'<span class="positive-percentage">{percentage:+.2f}%</span>'
    elif percentage < 0:
        return f'<span class="negative-percentage">{percentage:+.2f}%</span>'
    else:
        return f'<span class="neutral-percentage">{percentage:.2f}%</span>'

@st.dialog("Delete Portfolio")
def show_delete_confirmation_popup():
    portfolio_id = st.session_state.get('confirm_delete_portfolio')
    portfolio_name = st.session_state.get('confirm_delete_name', 'Unknown Portfolio')
    
    st.warning(f"**Confirm Deletion**")
    st.write(f"Are you sure you want to delete the portfolio **{portfolio_name}**?")
    st.write("**This action cannot be undone.**")
    st.write("")
    
    col_confirm, col_cancel = st.columns(2)
    
    with col_confirm:
        if st.button("Yes, Delete", type="primary", use_container_width=True):
            try:
                success, message = delete_portfolio(portfolio_id, st.session_state.username)
                
                if success:
                    st.success(f"Portfolio '{portfolio_name}' deleted successfully!")
                    del st.session_state.confirm_delete_portfolio
                    del st.session_state.confirm_delete_name
                    st.rerun()
                else:
                    st.error(f"Failed to delete portfolio: {message}")
                    
            except Exception as e:
                st.error(f"Error deleting portfolio: {str(e)}")
    
    with col_cancel:
        if st.button("Cancel", use_container_width=True):
            del st.session_state.confirm_delete_portfolio
            del st.session_state.confirm_delete_name
            st.rerun()

def get_company_news_link(symbol):
    try:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            company_name = info.get('longName', symbol)
        except Exception:
            company_name = symbol
        
        search_query = f"{company_name} {symbol} stock"
        encoded_query = quote(search_query)
        google_news_url = f"https://news.google.com/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        return {
            'company_name': company_name,
            'symbol': symbol,
            'search_query': search_query,
            'news_url': google_news_url
        }
        
    except Exception as e:
        st.error(f"Error generating news link: {str(e)}")
        return None

STOCK_SYMBOLS_BY_COUNTRY = {
    "United States": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "UNH", "JNJ",
        "V", "WMT", "JPM", "PG", "MA", "HD", "CVX", "ABBV", "PFE", "KO",
        "AVGO", "PEP", "COST", "TMO", "DHR", "MRK", "VZ", "ADBE", "WFC", "BAC",
        "NFLX", "CRM", "XOM", "LLY", "ABT", "ORCL", "ACN", "NVS", "CMCSA", "DIS",
        "CSCO", "TXN", "MDT", "PM", "QCOM", "HON", "RTX", "UPS", "LOW", "NKE",
        "INTC", "AMGN", "SPGI", "INTU", "CAT", "GS", "IBM", "SBUX", "AMD", "T"
    ],
    "United Kingdom": [
        "LLOY.L", "BP.L", "SHEL.L", "AZN.L", "ULVR.L", "VODGBP", "LSEG.L", "RIO.L", "HSBA.L", "GSK.L",
        "BARC.L", "NG.L", "DGE.L", "BT-A.L", "REL.L", "GLEN.L", "AAL.L", "NWG.L", "STAN.L", "PRU.L",
        "SSE.L", "CNA.L", "FLTR.L", "IAG.L", "RB.L", "CRDA.L", "INF.L", "LAND.L", "IMB.L", "III.L",
        "ADM.L", "ANTO.L", "AUTO.L", "AV.L", "BA.L", "BNZL.L", "BRBY.L", "CCL.L", "CPG.L", "CRDS.L",
        "EXPN.L", "FRAS.L", "HLMA.L", "IHG.L", "JET.L", "KGF.L", "LGEN.L", "MNG.L", "OCDO.L", "PSH.L",
        "RTO.L", "SGRO.L", "SMDS.L", "SPX.L", "TW.L", "UU.L", "VOD.L", "WTB.L", "3IN.L", "ABDN.L"
    ],
    "Australia": [
        "CBA.AX", "BHP.AX", "CSL.AX", "WBC.AX", "ANZ.AX", "NAB.AX", "WOW.AX", "FMG.AX", "MQG.AX", "WES.AX",
        "TLS.AX", "RIO.AX", "TCL.AX", "GMG.AX", "STO.AX", "QBE.AX", "ASX.AX", "COL.AX", "JHX.AX", "REA.AX",
        "AMP.AX", "ALL.AX", "APT.AX", "ASP.AX", "AWC.AX", "BEN.AX", "BKL.AX", "BLD.AX", "BOQ.AX", "BPT.AX",
        "BRG.AX", "BSL.AX", "BWP.AX", "CAR.AX", "CCP.AX", "CHC.AX", "CPU.AX", "CTX.AX", "CWN.AX", "DMP.AX",
        "DXS.AX", "ELD.AX", "EVN.AX", "FLT.AX", "GOR.AX", "GPT.AX", "HVN.AX", "IAG.AX", "IEL.AX", "IGO.AX",
        "ILU.AX", "IPL.AX", "JBH.AX", "LLC.AX", "MGR.AX", "MIN.AX", "NEC.AX", "NHF.AX", "NST.AX", "ORA.AX"
    ],
    "Hong Kong": [
        "0700.HK", "0941.HK", "0388.HK", "0005.HK", "1299.HK", "2318.HK", "0939.HK", "3690.HK", "0883.HK", "1398.HK",
        "2388.HK", "0267.HK", "0175.HK", "0002.HK", "0011.HK", "0016.HK", "0027.HK", "1109.HK", "0006.HK", "0001.HK",
        "0012.HK", "0017.HK", "0019.HK", "0023.HK", "0066.HK", "0083.HK", "0101.HK", "0144.HK", "0151.HK", "0200.HK",
        "0291.HK", "0293.HK", "0322.HK", "0386.HK", "0390.HK", "0392.HK", "0688.HK", "0762.HK", "0823.HK", "0857.HK",
        "0868.HK", "0881.HK", "0914.HK", "0916.HK", "0960.HK", "0968.HK", "0992.HK", "1044.HK", "1072.HK", "1093.HK",
        "1113.HK", "1171.HK", "1177.HK", "1211.HK", "1288.HK", "1336.HK", "1378.HK", "1816.HK", "1880.HK", "1928.HK"
    ],
    "China": [
        "BABA", "JD", "BIDU", "NIO", "PDD", "BILI", "TME", "IQ", "NTES", "VIPS",
        "YMM", "LI", "XPEV", "EDU", "TAL", "WB", "DOYU", "KC", "TUYA", "DADA",
        "YSG", "TIGR", "FUTU", "RLX", "GOTU", "MOMO", "HUYA", "DOCU", "ZTO", "YTO",
        "STO", "BEST", "QFIN", "LKNCY", "ZLAB", "CAAS", "CBPO", "CANG", "CAN", "CARS",
        "CADC", "CXDC", "DQ", "EH", "FENG", "GSMG", "HEAR", "HCM", "HIMX", "HUIZ",
        "JOBS", "LAIX", "LX", "NAAS", "NIU", "QTT", "RERE", "SOHU", "TOUR", "WDH"
    ]
}

@st.cache_data(ttl=86400)
def get_stock_data(symbol, days):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        
        return data
    except Exception as e:
        st.error(f"Failed to fetch data for {symbol}: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

@st.cache_data(ttl=86400)
def get_historical_stock_data(symbol, start_year=2000):
    try:
        start_date = datetime(start_year, 1, 1)
        end_date = datetime.now()
        
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        
        return data
    except Exception as e:
        st.error(f"Failed to fetch historical data for {symbol}: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

def get_stock_info_with_history(symbol):
    try:
        ticker = yf.Ticker(symbol)
        
        info = ticker.info
        
        historical_data = get_historical_stock_data(symbol, 2000)
        
        recent_data = ticker.history(period="2d")
        
        stock_info = {
            "symbol": symbol,
            "name": info.get('longName', info.get('shortName', symbol)),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "historical_data": historical_data,
            "info": info
        }
        
        if not recent_data.empty and len(recent_data) >= 2:
            current_price = float(recent_data['Close'].iloc[-1])
            previous_price = float(recent_data['Close'].iloc[-2])
            change = current_price - previous_price
            
            stock_info.update({
                "price": current_price,
                "change": change,
                "previous_price": previous_price
            })
        
        return stock_info
        
    except Exception as e:
        st.error(f"Failed to fetch complete info for {symbol}: {str(e)}")
        return None

@st.cache_data(ttl=3600)
def get_stocks_for_search(country):
    if country not in STOCK_SYMBOLS_BY_COUNTRY:
        return []
    
    symbols = STOCK_SYMBOLS_BY_COUNTRY[country]
    stock_data = []
    
    try:
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            batch_string = " ".join(batch)
            
            try:
                tickers = yf.Tickers(batch_string)
                
                for symbol in batch:
                    try:
                        ticker = tickers.tickers[symbol]
                        info = ticker.info
                        hist = ticker.history(period="2d")
                        
                        if not hist.empty and len(hist) >= 2:
                            current_price = float(hist['Close'].iloc[-1])
                            previous_price = float(hist['Close'].iloc[-2])
                            change = current_price - previous_price
                            
                            stock_data.append({
                                "symbol": symbol,
                                "name": info.get('longName', info.get('shortName', symbol)),
                                "price": current_price,
                                "change": change,
                                "country": country
                            })
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
                
    except Exception as e:
        st.error(f"Error fetching stock data: {str(e)}")
    
    return stock_data

@st.cache_data(ttl=86400)
def get_multiple_stocks_data(symbols, days):
    stock_data = {}
    for symbol in symbols:
        try:
            data = get_stock_data(symbol, days)
            if isinstance(data, pd.DataFrame) and not data.empty:
                stock_data[symbol] = data
        except Exception as e:
            continue
    return stock_data

def login_page(go_to, verify_user, update_last_login):
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                if verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    update_last_login(username)
                    st.success("Login successful!")
                    go_to("dashboard")
                else:
                    st.error("Invalid credentials")

    st.divider()

    st.write("Don't have an account?")
    if st.button("Register here", use_container_width=True):
        go_to("register")

def register_page(go_to, register_user):
    st.title("Register")

    username = st.text_input("Choose a username")
    email = st.text_input("Email")
    password = st.text_input(
        "Choose a password",
        type="password",
        help="Must be at least 8 characters with uppercase, lowercase, number and special character",
    )
    confirm_password = st.text_input("Confirm password", type="password")

    if password and confirm_password:
        if password == confirm_password:
            st.success("Passwords match")
        else:
            st.error("Passwords don't match")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Register", type="primary", use_container_width=True):
            success, message = register_user(username, password, email)
            if success:
                st.success(message)
                st.balloons()  # Celebration animation
                go_to("login")
            else:
                st.error(message)

    with col2:
        if st.button("Back to login", use_container_width=True):
            go_to("login")

def dashboard_page(go_to, get_user_info, change_password):
    with st.sidebar:
        st.header("Menu")
        
        st.subheader("Options")
        
        if st.button("Detailed Stock Analysis", use_container_width=True, key="sidebar_stock_analysis"):
            go_to("stock_analysis")
        
        if st.button("Portfolios", use_container_width=True):
            go_to("portfolios")
        
        if st.button("Logout", use_container_width=True):
            handle_logout()
        
        st.divider()
        
        st.subheader("Quick Info")
    
    st.title("Dashboard")

    user_info = get_user_info(st.session_state.username)

    st.markdown(f"### Welcome back, **{st.session_state.username}**!")

    if user_info and user_info.get("last_login"):
        last_login = user_info["last_login"]
        if isinstance(last_login, datetime):
            last_login_formatted = last_login.strftime("%Y-%m-%d %H:%M:%S")

    if user_info:
        days_since = (
            datetime.utcnow() - user_info.get("created_at", datetime.utcnow())
        ).days

    st.divider()

    st.subheader("Quick Actions")

    user_portfolios = get_user_portfolios(st.session_state.username)
    
    if user_portfolios:
        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            if st.button("Create New Portfolio", type="primary", use_container_width=True):
                go_to("create_portfolio")
        with action_col2:
            if st.button("View All Portfolios", use_container_width=True):
                go_to("portfolios")
        with action_col3:
            if st.button("Search Stocks", use_container_width=True):
                go_to("stock_analysis")
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create Your First Portfolio", type="primary", use_container_width=True):
                go_to("create_portfolio")
        with col2:
            if st.button("Detailed Stock Analysis", use_container_width=True, key="dashboard_stock_analysis"):
                go_to("stock_analysis")

    st.divider()

    st.subheader("Your Portfolios Summary")
    
    if user_portfolios:
        total_portfolios = len(user_portfolios)
        total_stocks = sum(len(p.get('stocks', [])) for p in user_portfolios)
        
        total_invested = 0
        for portfolio in user_portfolios:
            for stock in portfolio.get('stocks', []):
                purchase_price = stock.get('purchase_price', stock.get('price', 0))
                total_invested += purchase_price * stock.get('shares', 1)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Portfolios", total_portfolios)
        with col2:
            st.metric("Total Stocks", total_stocks)
        with col3:
            st.metric("Total Invested", f"${total_invested:,.2f}")
        with col4:
            avg_portfolio_value = total_invested / total_portfolios if total_portfolios > 0 else 0
            st.metric("Avg Portfolio", f"${avg_portfolio_value:,.2f}")
        
        st.divider()
        
        st.subheader("Portfolio Overview")
        
        portfolio_data = []

        for portfolio in user_portfolios:
                stocks = portfolio.get('stocks', [])
                stock_count = len(stocks)
                countries = portfolio.get('countries', [])

                invested = 0
                for stock in stocks:
                    purchase_price = stock.get('purchase_price', stock.get('price', 0))
                    invested += purchase_price * stock.get('shares', 1)

                predicted_value = 0
                if stocks:
                    for stock in stocks:
                        try:
                            ticker = yf.Ticker(stock['symbol'])
                            hist_data = ticker.history(period="2y")

                            if not hist_data.empty and len(hist_data) >= 30:
                                price_data = hist_data['Close'].dropna()

                                prediction = calculate_stock_prediction(price_data, future_days=365)

                                if prediction:
                                    predicted_price = prediction['predicted_price']
                                    shares = stock.get('shares', 1)
                                    predicted_value += predicted_price * shares
                                else:
                                    current_price = stock.get('price', 0)
                                    shares = stock.get('shares', 1)
                                    predicted_value += current_price * shares
                            else:
                                current_price = stock.get('price', 0)
                                shares = stock.get('shares', 1)
                                predicted_value += current_price * shares
                        except Exception as e:
                            current_price = stock.get('price', 0)
                            shares = stock.get('shares', 1)
                            predicted_value += current_price * shares

                predicted_change = predicted_value - invested
                predicted_change_pct = (predicted_change / invested * 100) if invested > 0 else 0

                top_holdings = []
                for stock in stocks[:3]:
                    purchase_price = stock.get('purchase_price', stock.get('price', 0))
                    stock_value = purchase_price * stock.get('shares', 1)
                    top_holdings.append(f"{stock.get('symbol', 'N/A')} ({stock.get('shares', 1)} shares)")

                top_holdings_str = ", ".join(top_holdings) if top_holdings else "No stocks"
                if len(stocks) > 3:
                    top_holdings_str += f" + {len(stocks) - 3} more"

                portfolio_data.append({
                    "Portfolio Name": portfolio.get('portfolio_name', 'Unnamed Portfolio'),
                    "Total Value": f"${invested:,.2f}",
                    "Predicted Value (1Y)": f"${predicted_value:,.2f}",
                    "Expected Change": f"{predicted_change_pct:+.1f}%",
                    "Stocks": stock_count,
                    "Markets": ", ".join(countries) if countries else "N/A",
                    "Top Holdings": top_holdings_str
                })
        
        if portfolio_data:
            df = pd.DataFrame(portfolio_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
                
    else:

    st.divider()

    st.subheader("Community Portfolios")

    all_portfolios = get_all_portfolios()

    if all_portfolios:
        other_users_portfolios = [p for p in all_portfolios if p.get('user_id') != st.session_state.username]
        media_portfolios = other_users_portfolios[:5]  # Limit to first 5 for display

        if media_portfolios:
            for portfolio in media_portfolios:
                    owner_username = portfolio.get('user_id', 'Unknown User')
                    stocks = portfolio.get('stocks', [])
                    stock_count = len(stocks)
                    countries = portfolio.get('countries', [])
                    created_at = portfolio.get('created_at')

                    total_value = 0
                    for stock in stocks:
                        purchase_price = stock.get('purchase_price', stock.get('price', 0))
                        total_value += purchase_price * stock.get('shares', 1)

                    predicted_value = 0
                    if stocks:
                        for stock in stocks:
                            try:
                                ticker = yf.Ticker(stock['symbol'])
                                hist = ticker.history(period="1y")

                                if len(hist) >= 30:
                                    price_data = hist['Close'].dropna()

                                    prediction = calculate_stock_prediction(price_data, future_days=365)

                                    if prediction:
                                        predicted_price = prediction['predicted_price']
                                        shares = stock.get('shares', 1)
                                        predicted_value += predicted_price * shares
                                    else:
                                        current_price = stock.get('price', 0)
                                        shares = stock.get('shares', 1)
                                        predicted_value += current_price * shares
                                else:
                                    current_price = stock.get('price', 0)
                                    shares = stock.get('shares', 1)
                                    predicted_value += current_price * shares
                            except Exception as e:
                                current_price = stock.get('price', 0)
                                shares = stock.get('shares', 1)
                                predicted_value += current_price * shares

                    predicted_change = predicted_value - total_value
                    predicted_change_pct = (predicted_change / total_value * 100) if total_value > 0 else 0

                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])

                        with col1:
                            st.write(f"**{owner_username}**")
                            if created_at:

                        with col2:
                            st.metric("Purchase Value", f"${total_value:,.2f}")

                        with col3:
                            st.metric("Predicted Value (1Y)", f"${predicted_value:,.2f}", f"{predicted_change_pct:+.1f}%")

                        with col4:
                            st.metric("Stocks", stock_count)

                        with col5:
                            if st.button("View Details", key=f"media_view_{portfolio['_id']}", use_container_width=True):
                                st.session_state.media_portfolio_id = str(portfolio['_id'])
                                st.session_state.media_portfolio_owner = owner_username
                                go_to("media_portfolio_view")

                    if stocks:
                        holdings_text = "Holdings: " + ", ".join([f"{s.get('symbol', 'N/A')}" for s in stocks[:3]])
                        if len(stocks) > 3:
                            holdings_text += f" +{len(stocks) - 3} more"

                    st.markdown("---")

            if len(other_users_portfolios) > 10:
        else:
    else:

    st.divider()

    st.subheader("Global Stock Market Dashboard")

    days = 365  # 1 year
    all_countries_data = {}

    for country, symbols in STOCK_SYMBOLS_BY_COUNTRY.items():
        top_symbols = symbols[:6]
        country_data = get_multiple_stocks_data(top_symbols, days)
        if country_data:
            all_countries_data[country] = country_data
    
    if all_countries_data:
        country_tabs = st.tabs(list(all_countries_data.keys()))
        
        for tab, (country, country_data) in zip(country_tabs, all_countries_data.items()):
            with tab:
                st.write(f"### {country} Stock Market")
                
                if country_data:
                    cols = st.columns(3)  # 3 columns for the grid (6 stocks = 2 rows)
                    
                    for idx, (symbol, data) in enumerate(country_data.items()):
                        with cols[idx % 3]:  # Distribute across 3 columns
                            try:
                                if isinstance(data, pd.DataFrame) and not data.empty:
                                    latest = data.iloc[-1]
                                    previous = data.iloc[-2] if len(data) > 1 else latest
                                    
                                    change = float(latest["Close"]) - float(previous["Close"])
                                    prev_close = float(previous["Close"])
                                    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
                                    
                                    with st.container():
                                        st.markdown(f"**{symbol}**")
                                        
                                        st.metric("Price", f"${float(latest['Close']):.2f}", delta=f"{change_pct:+.2f}%")
                                        
                                        if 'Close' in data.columns and len(data) > 1:
                                            chart_data = data['Close'].tail(365).round(2)  # Show only last 365 days, rounded to 2dp
                                            st.line_chart(chart_data, height=150)
                                        
                                        st.markdown("---")
                                        
                            except Exception as e:
                                with st.container():
                                    st.error(f"Error loading {symbol}: {str(e)}")
                                    st.markdown("---")
                else:
                    st.warning(f"Unable to load {country} stock data.")
        
    else:
        st.warning("Unable to load stock data. Please check your internet connection.")

def stock_analysis_page(go_to, get_user_info, change_password):
    with st.sidebar:
        st.header("Stock Analysis")
        
        st.subheader("Stock Search")
        
        all_stock_symbols = []
        for country, symbols in STOCK_SYMBOLS_BY_COUNTRY.items():
            all_stock_symbols.extend(symbols)
        
        all_stock_symbols = sorted(list(set(all_stock_symbols)))
        
        search_query = st.text_input(
            "Search Stock Symbol",
            value="AAPL",
            placeholder="Type to search (e.g., AAPL, GOOGL, TSLA...)",
            help="Search from all available stocks across US, UK, Australia, Hong Kong, and China markets"
        )
        
        if search_query:
            filtered_stocks = [stock for stock in all_stock_symbols if search_query.upper() in stock.upper()]
            
            if filtered_stocks:
                if len(filtered_stocks) > 10:
                    display_stocks = filtered_stocks[:10]
                else:
                    display_stocks = filtered_stocks
                
                cols = st.columns(2)
                for idx, stock in enumerate(display_stocks):
                    with cols[idx % 2]:
                        if st.button(stock, key=f"search_{stock}", use_container_width=True):
                            st.session_state.selected_stock_symbol = stock
                            search_query = stock
                            st.rerun()
                
                selected_stock = search_query.upper() if search_query.upper() in [s.upper() for s in all_stock_symbols] else filtered_stocks[0]
            else:
                st.warning("No stocks found matching your search. Try different keywords.")
                selected_stock = "AAPL"  # Default fallback
        else:
            selected_stock = "AAPL"  # Default when no search
        
        if hasattr(st.session_state, 'selected_stock_symbol'):
            selected_stock = st.session_state.selected_stock_symbol
        

        st.subheader("Analysis Tools")
        show_volume = st.checkbox("Show Volume", value=True)
        show_moving_avg = st.checkbox("Show Moving Average", value=False)
        
        st.divider()
        
        if st.button("← Back to Dashboard", use_container_width=True):
            go_to("dashboard")
        
        if st.button("Portfolios", use_container_width=True):
            go_to("portfolios")
        
        if st.button("Logout", use_container_width=True):
            handle_logout()
    
    st.title(f"{selected_stock} - Detailed Analysis")
    
    analysis_days = 3650  # 10 years (10 * 365)
    data = get_stock_data(selected_stock, analysis_days)
    
    if isinstance(data, pd.DataFrame) and not data.empty:
        latest = data.iloc[-1]
        previous = data.iloc[-2] if len(data) > 1 else latest
        
        change = float(latest["Close"]) - float(previous["Close"])
        prev_close = float(previous["Close"])
        change_pct = (change / prev_close) * 100 if prev_close != 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**Current Price**")
            st.markdown(f"${float(latest['Close']):.2f}")
            st.markdown(f"{change:+.2f} ({format_percentage_with_color(change_pct)})", unsafe_allow_html=True)
        with col2:
            st.metric("52-Week High", f"${float(data['High'].max()):.2f}")
        with col3:
            st.metric("52-Week Low", f"${float(data['Low'].min()):.2f}")
        with col4:
            try:
                volume = int(float(latest['Volume']))
                st.metric("Volume", f"{volume:,}")
            except Exception:
                st.metric("Volume", "N/A")
        
        st.divider()
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.subheader(f"{selected_stock} Price Chart")
            
            try:
                if 'Close' in data.columns:
                    chart_data = pd.DataFrame({'Close': data['Close']})
                    if show_moving_avg and len(data) >= 20:
                        chart_data['20-Day MA'] = data['Close'].rolling(window=20).mean()
                    
                    st.line_chart(chart_data, height=400)
                else:
                    st.error("Close price data not available")
            except Exception as e:
                st.error(f"Error creating price chart: {str(e)}")
        
        with col2:
            try:
                if show_volume and 'Volume' in data.columns:
                    st.subheader("Volume Chart")
                    volume_data = pd.DataFrame({'Volume': data['Volume']})
                    st.bar_chart(volume_data, height=400)
                elif 'High' in data.columns and 'Low' in data.columns:
                    st.subheader("High-Low Range")
                    high_low_data = pd.DataFrame({
                        'High': data['High'],
                        'Low': data['Low']
                    })
                    st.line_chart(high_low_data, height=400)
                else:
                    st.error("Chart data not available")
            except Exception as e:
                st.error(f"Error creating secondary chart: {str(e)}")
        
        st.divider()
        
        col1, col2 = st.columns([2, 3])
        
        with col1:
            st.subheader("Recent Performance")
            
            periods = [1, 7, 30]
            performance_data = []
            
            for period in periods:
                if len(data) > period:
                    old_price = float(data.iloc[-(period+1)]['Close'])
                    current_price = float(latest['Close'])
                    change = ((current_price - old_price) / old_price) * 100
                    performance_data.append({
                        'Period': f'{period} Day{"s" if period > 1 else ""}',
                        'Change (%)': f'{change:+.2f}%'
                    })
            
            if performance_data:
                st.table(pd.DataFrame(performance_data))
        
        with col2:
            st.subheader("Price Statistics")
            
            stats_data = [
                {'Metric': 'Average', 'Value': f"${data['Close'].mean():.2f}"},
                {'Metric': 'Median', 'Value': f"${data['Close'].median():.2f}"},
                {'Metric': 'Std Deviation', 'Value': f"${data['Close'].std():.2f}"},
                {'Metric': 'Range', 'Value': f"${data['Close'].max() - data['Close'].min():.2f}"}
            ]
            st.table(pd.DataFrame(stats_data))

        st.divider()
        st.subheader("Price Prediction Using Linear Regression")

        price_data = data['Close'].dropna()

        if len(price_data) >= 30:  # Need at least 30 days of data
            prediction = calculate_stock_prediction(price_data, future_days=365)

            if prediction:
                current_price = prediction['current_price']
                predicted_1year = prediction['predicted_price']
                predicted_change = predicted_1year - current_price
                predicted_change_pct = (predicted_change / current_price) * 100

                pred_col1, pred_col2, pred_col3 = st.columns(3)

                with pred_col1:
                    st.metric("Current Price", f"${current_price:.2f}")
                with pred_col2:
                    st.metric("Predicted Price (1 Year)", f"${predicted_1year:.2f}", f"{predicted_change:+.2f} ({predicted_change_pct:+.2f}%)")
                with pred_col3:
                    st.metric("Model R² Score", f"{prediction['r_squared']:.4f}")

                st.subheader("Prediction Visualization")

                lookback_days = min(730, len(price_data))  # 2 years or less
                recent_data = price_data.tail(lookback_days)
                recent_dates = recent_data.index

                last_date = recent_dates[-1]
                future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=365, freq='D')

                recent_X = np.arange(len(price_data) - lookback_days, len(price_data))
                recent_pred = prediction['slope'] * recent_X + prediction['intercept']

                combined_dates = list(recent_dates) + list(future_dates)
                combined_actual = list(recent_data.values) + [None] * 365
                combined_predicted = list(recent_pred) + list(prediction['future_predictions'])

                combined_df = pd.DataFrame({
                    'Historical Price': combined_actual,
                    'Predicted Trend': [None] * lookback_days + list(prediction['future_predictions'])
                }, index=combined_dates)

                st.line_chart(combined_df, height=400)

                with st.expander("View Model Details"):
                    st.write(f"**Regression Equation:** Price = {prediction['slope']:.4f} × Days + {prediction['intercept']:.2f}")
                    st.write(f"**Daily Trend:** {'Upward ↗' if prediction['slope'] > 0 else 'Downward ↘'} (${prediction['slope']:.4f} per day)")
                    st.write(f"**Training Data Points:** {len(price_data)} days")
                    st.write(f"**Prediction Period:** 365 days (1 year)")
            else:
                st.warning("Unable to generate prediction with available data.")
        else:
            st.warning("Not enough historical data for regression analysis. Need at least 30 days.")

        st.divider()
        st.subheader(" Company News")
        
        news_info = get_company_news_link(selected_stock)
        
        if news_info:
            st.write(f"**Company:** {news_info['company_name']}")
            st.write(f"**Stock Symbol:** {news_info['symbol']}")
            st.write(f"**Search Query:** {news_info['search_query']}")
            
            st.link_button(
                f"View {news_info['company_name']} News on Google", 
                news_info['news_url'],
                use_container_width=True
            )
            
        else:
        
        
    else:
        st.error(f"Unable to load data for {selected_stock}")

def portfolios_page(go_to, get_user_info, change_password):
    with st.sidebar:
        st.header("Portfolio Manager")
        
        st.subheader("Actions")
        
        if st.button("Create New Portfolio", use_container_width=True):
            go_to("create_portfolio")
        
        if st.button("Portfolio Analytics", use_container_width=True):
            if 'analytics_portfolio_id' in st.session_state:
                del st.session_state.analytics_portfolio_id
            go_to("portfolio_analytics")

        st.divider()
        
        if st.button("← Back to Dashboard", use_container_width=True):
            go_to("dashboard")
        
        if st.button("Stock Analysis", use_container_width=True):
            go_to("stock_analysis")
        
        if st.button("Logout", use_container_width=True):
            handle_logout()
    
    st.title("Portfolio Management")
    
    st.header("Summary")

    user_portfolios = get_user_portfolios(st.session_state.username)
    
    sample_portfolios = []
    for portfolio in user_portfolios:
        total_value = sum(stock.get('price', 0) * stock.get('shares', 1) for stock in portfolio.get('stocks', []))
        
        sample_portfolios.append({
            "_id": str(portfolio['_id']),
            "name": portfolio['portfolio_name'],
            "created": portfolio['created_at'].strftime('%Y-%m-%d') if portfolio.get('created_at') else "Unknown",
            "value": total_value,
            "change": 0,  # Placeholder - would calculate from historical data
            "change_pct": 0,  # Placeholder - would calculate from historical data
            "stocks": [stock['symbol'] for stock in portfolio.get('stocks', [])]
        })
    
    if sample_portfolios:
        total_value = sum(p["value"] for p in sample_portfolios)
        total_change = sum(p["change"] for p in sample_portfolios)
        
        denominator = total_value - total_change
        if denominator != 0 and total_value != 0:
            total_change_pct = (total_change / denominator) * 100
        else:
            total_change_pct = 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Portfolio Value", f"${total_value:,.2f}", f"{total_change:+.2f} ({total_change_pct:+.2f}%)")
        with col2:
            st.metric("Number of Portfolios", len(sample_portfolios))
        with col3:
            best_performer = max(sample_portfolios, key=lambda p: p["change_pct"])
            st.metric("Best Performer", best_performer["name"], f"{best_performer['change_pct']:+.2f}%")
        with col4:
            st.metric("Active Portfolios", len([p for p in sample_portfolios if p.get('value', 0) > 0]))
    else:
    
    st.divider()
    
    st.header("My Portfolios")
    
    if sample_portfolios:
        sorted_portfolios = sorted(sample_portfolios, key=lambda p: p['value'], reverse=True)
        
        for portfolio in sorted_portfolios:
            with st.container():
                col1, col2 = st.columns([3, 2])
                
                with col1:
                    st.markdown(f"### {portfolio['name']}")
                    st.write(f"**Created:** {portfolio['created']}")
                    st.write(f"**Holdings:** {', '.join(portfolio['stocks'])}")
                
                with col2:
                    st.metric(
                        "Current Value",
                        f"${portfolio['value']:.2f}",
                        f"{portfolio['change']:+.2f} ({portfolio['change_pct']:+.2f}%)"
                    )
                
                col_view, col_edit, col_share, col_delete = st.columns(4)
                with col_view:
                    if st.button(f"View", key=f"view_{portfolio['name']}"):
                        st.session_state.view_portfolio_id = portfolio['_id']
                        st.session_state.view_portfolio_name = portfolio['name']
                        go_to("portfolio_details")
                
                with col_edit:
                    if st.button(f"Edit", key=f"edit_{portfolio['name']}"):
                        st.session_state.edit_portfolio_id = portfolio['_id']
                        st.session_state.edit_portfolio_name = portfolio['name']
                        go_to("edit_portfolio")
                
                with col_share:
                    if st.button(f"Share", key=f"share_{portfolio['name']}"):
                        st.session_state.share_portfolio = {
                            '_id': portfolio['_id'],
                            'name': portfolio['name'],
                            'value': portfolio['value'],
                            'stocks': portfolio['stocks']
                        }
                
                with col_delete:
                    if st.button(f"Delete", key=f"delete_{portfolio['name']}", type="secondary"):
                        st.session_state.confirm_delete_portfolio = portfolio['_id']
                        st.session_state.confirm_delete_name = portfolio['name']
                        st.rerun()
                
                if st.session_state.get('share_portfolio') and st.session_state.share_portfolio['_id'] == portfolio['_id']:
                    with st.expander(f"Share Portfolio: {portfolio['name']}", expanded=True):
                        st.write("**Share your portfolio with others:**")
                        
                        share_data = st.session_state.share_portfolio
                        
                        portfolio_url = f"https://yourapp.com/shared-portfolio/{share_data['_id']}"
                        
                        share_text = f"""
Investment Portfolio Template: "{share_data['name']}"

Portfolio Composition:
{len(share_data['stocks'])} stocks: {', '.join(share_data['stocks'])}

Create your own version of this portfolio!
View Template: {portfolio_url}
                        """.strip()
                        
                        
                        col_share_left, col_share_right = st.columns(2)
                        
                        with col_share_left:
                            st.write("**Share Portfolio Template**")
                            st.text_area("Portfolio Template Message", value=share_text, height=120, key=f"share_text_{share_data['_id']}")
                            
                            col_copy, col_close = st.columns(2)
                            with col_copy:
                                if st.button("Copy Template", key=f"copy_template_{share_data['_id']}", type="primary"):
                                    st.success("Portfolio template copied to clipboard!")
                            
                            with col_close:
                                if st.button("Close", key=f"close_share_{share_data['_id']}"):
                                    del st.session_state.share_portfolio
                                    st.rerun()
                        
                        with col_share_right:
                            st.write("**Portfolio Composition**")
                            st.write("**Stock Holdings:**")
                            for stock in share_data['stocks']:
                                st.write(f"• {stock}")
                            
                            st.write("---")
                            st.write("**What others get:**")
                            
                            st.write("**Share URL:**")
                            st.code(portfolio_url, language=None)
                            
                            if st.button("Generate Share Link", key=f"generate_link_{share_data['_id']}"):
                                st.success("Shareable link generated!")
                
                st.markdown("---")
    
    if st.session_state.get('confirm_delete_portfolio'):
        show_delete_confirmation_popup()
    
    if st.session_state.get("show_create_form", False):
        st.subheader("Create New Portfolio")
        
        with st.form("create_portfolio"):
            portfolio_name = st.text_input("Portfolio Name", placeholder="e.g., Tech Growth Portfolio")
            portfolio_desc = st.text_area("Description (Optional)", placeholder="Brief description of your investment strategy")
            
            st.write("**Select Initial Stocks (Optional):**")
            available_stocks = ["AAPL", "GOOGL", "AMZN", "MSFT", "TSLA", "META", "NFLX", "NVDA"]
            selected_stocks = st.multiselect("Choose stocks to add", available_stocks)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Create Portfolio", type="primary"):
                    if portfolio_name:
                        st.success(f"Portfolio '{portfolio_name}' created successfully!")
                        st.balloons()
                        st.session_state.show_create_form = False
                        st.rerun()
                    else:
                        st.error("Please enter a portfolio name")
            
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.show_create_form = False
                    st.rerun()
    
    if st.session_state.get("show_analytics", False):
        st.subheader("Portfolio Analytics & Predictions")

        if not user_portfolios:
            if st.button("Hide Analytics"):
                st.session_state.show_analytics = False
                st.rerun()
        else:
            all_stocks = []
            for portfolio in user_portfolios:
                for stock in portfolio.get('stocks', []):
                    stock_info = {
                        'symbol': stock['symbol'],
                        'name': stock.get('name', stock['symbol']),
                        'shares': stock.get('shares', 1),
                        'purchase_price': stock.get('purchase_price', stock.get('price', 0)),
                        'portfolio_name': portfolio['portfolio_name']
                    }
                    all_stocks.append(stock_info)

            if not all_stocks:
                if st.button("Hide Analytics"):
                    st.session_state.show_analytics = False
                    st.rerun()
            else:
                st.subheader("Overall Portfolio Value Prediction")

                total_current_value = 0
                total_predicted_value = 0
                portfolio_predictions = []

                for stock_info in all_stocks:
                    try:
                        ticker = yf.Ticker(stock_info['symbol'])
                        hist_data = ticker.history(period="2y")

                        if not hist_data.empty and len(hist_data) >= 30:
                            price_data = hist_data['Close'].dropna()

                            prediction = calculate_stock_prediction(price_data, future_days=365)

                            if prediction:
                                current_price = prediction['current_price']
                                predicted_price = prediction['predicted_price']
                                shares = stock_info['shares']

                                current_stock_value = current_price * shares
                                predicted_stock_value = predicted_price * shares

                                total_current_value += current_stock_value
                                total_predicted_value += predicted_stock_value

                                portfolio_predictions.append({
                                    'symbol': stock_info['symbol'],
                                    'name': stock_info['name'],
                                    'shares': shares,
                                    'current_price': current_price,
                                    'predicted_price': predicted_price,
                                    'current_value': current_stock_value,
                                    'predicted_value': predicted_stock_value,
                                    'prediction': prediction
                                })
                    except Exception as e:
                        st.warning(f"Could not analyze {stock_info['symbol']}: {str(e)}")
                        continue

                if portfolio_predictions:
                    value_change = total_predicted_value - total_current_value
                    value_change_pct = (value_change / total_current_value * 100) if total_current_value > 0 else 0

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Current Portfolio Value", f"${total_current_value:,.2f}")
                    with col2:
                        st.metric("Predicted Value (1 Year)", f"${total_predicted_value:,.2f}", f"{value_change:+,.2f} ({value_change_pct:+.2f}%)")
                    with col3:
                        trend = "Upward" if value_change > 0 else "Downward"
                        st.metric("Trend", trend)

                    st.divider()

                    st.subheader("Individual Stock Predictions")

                    for pred in portfolio_predictions:
                        with st.expander(f"{pred['symbol']} - {pred['name']}", expanded=False):
                            stock_change = pred['predicted_price'] - pred['current_price']
                            stock_change_pct = (stock_change / pred['current_price'] * 100) if pred['current_price'] > 0 else 0

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Current Price", f"${pred['current_price']:.2f}")
                            with col2:
                                st.metric("Predicted Price (1 Year)", f"${pred['predicted_price']:.2f}", f"{stock_change:+.2f} ({stock_change_pct:+.2f}%)")
                            with col3:
                                st.metric("Total Value Change", f"${pred['predicted_value'] - pred['current_value']:+,.2f}")

                            st.write("**Price Prediction Chart**")

                            if 'prediction' in pred:
                                st.line_chart(pd.DataFrame({
                                    'Predicted Price': pred['prediction']['future_predictions']
                                }), height=300)
                else:
                    st.warning("Could not generate predictions. Make sure your stocks have sufficient historical data.")

                st.divider()

                if st.button("Hide Analytics"):
                    st.session_state.show_analytics = False
                    st.rerun()

def create_portfolio_page(go_to, get_user_info, change_password):
    with st.sidebar:
        st.header("Create New Portfolio")
        
        st.divider()
        
        if st.button("← Back to Portfolios", use_container_width=True):
            go_to("portfolios")
        
        if st.button("Dashboard", use_container_width=True):
            go_to("dashboard")
        
        if st.button("Logout", use_container_width=True):
            handle_logout()
    
    st.title("Create New Portfolio")
    st.markdown("### Let's build your investment portfolio step by step")
    
    st.divider()
    
    with st.form("create_portfolio_form", clear_on_submit=False):
        
        st.subheader("Which countries would you like to invest in?")
        
        countries = [
            "United States", "Canada", "United Kingdom", "Germany", "France", 
            "Japan", "Australia", "South Korea", "India", "China", 
            "Brazil", "Netherlands", "Switzerland", "Sweden", "Denmark"
        ]
        
        selected_countries = st.multiselect(
            "Select countries/regions for investment",
            options=countries,
            default=["United States"],
            help="Choose the countries where you'd like to invest. This will help us recommend appropriate stocks and ETFs."
        )
        
        st.divider()
        
        st.subheader("Portfolio Details")
        portfolio_name = st.text_input(
            "Portfolio Name", 
            placeholder="e.g., My Global Growth Portfolio",
            help="Give your portfolio a memorable name"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("Create Portfolio", type="primary", use_container_width=True)
        
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
    
    if submitted:
        if portfolio_name and selected_countries:

            portfolio_data = {
                'name': portfolio_name,
                'countries': selected_countries,
                'stocks': []
            }
            
            success, message = create_portfolio(st.session_state.username, portfolio_data)
            
            if success:
                st.success("Portfolio created successfully!")
                st.balloons()
                
                st.subheader("Portfolio Summary")
                st.write(f"**Name:** {portfolio_name}")
                st.write(f"**Countries:** {', '.join(selected_countries)}")
                

                user_portfolios = get_user_portfolios(st.session_state.username)

                if user_portfolios:
                    latest_portfolio = user_portfolios[0]  # Sorted by created_at desc
                    st.session_state.current_portfolio = portfolio_data
                    st.session_state.current_portfolio['_id'] = str(latest_portfolio['_id'])
                else:
                    st.session_state.current_portfolio = portfolio_data
                    st.session_state.current_portfolio['_id'] = 'temp_id'

                go_to("my_stocks")
            else:
                st.error(f"{message}")
            
        else:
            st.error("Please fill in all required fields (Portfolio name and at least one country)")
    
    elif cancelled:
        go_to("portfolios")

def my_stocks_page(go_to, get_user_info, change_password):
    with st.sidebar:
        st.header("My Stocks")
        
        if 'current_portfolio' in st.session_state:
            portfolio = st.session_state.current_portfolio
            st.write(f"**Portfolio:** {portfolio['name']}")
            st.write(f"**Countries:** {', '.join(portfolio['countries'])}")
        
        st.divider()
        
        st.subheader("Actions")
        
        if st.button("Add Stock", use_container_width=True, type="primary"):
            go_to("stock_search")
        
        if st.button(" Portfolio Analytics", use_container_width=True):
            if 'current_portfolio' in st.session_state:
                st.session_state.analytics_portfolio_id = st.session_state.current_portfolio.get('_id')
            go_to("portfolio_analytics")

        st.divider()
        
        if st.button("← Back to Portfolios", use_container_width=True):
            go_to("portfolios")
        
        if st.button("Dashboard", use_container_width=True):
            go_to("dashboard")
        
        if st.button("Logout", use_container_width=True):
            handle_logout()
    
    st.title("My Portfolio")
    
    portfolio = None
    if 'current_portfolio' in st.session_state:
        portfolio_id = st.session_state.current_portfolio.get('_id')
        if portfolio_id and portfolio_id != 'temp_id':
            portfolio = get_portfolio_by_id(portfolio_id)
        
        if not portfolio:
            portfolio = st.session_state.current_portfolio
    
    if portfolio:
        portfolio_name = portfolio.get('portfolio_name', portfolio.get('name', 'Unknown Portfolio'))
        st.markdown(f"### Portfolio: **{portfolio_name}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Stocks Added", len(portfolio.get('stocks', [])))
        with col2:
            total_value = sum(stock.get('price', 0) * stock.get('shares', 1) for stock in portfolio.get('stocks', []))
            st.metric("Total Value", f"${total_value:,.2f}")
    
    st.divider()
    
    st.subheader("Stock Holdings")
    
    if portfolio and portfolio.get('stocks'):
        stocks = portfolio['stocks']  # Use database stocks
        
        for idx, stock in enumerate(stocks):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1.5, 1])
                
                with col1:
                    st.write(f"**{stock['symbol']}**")
                
                with col2:
                    st.write(f"${stock.get('price', 0):.2f}")
                
                with col3:
                    st.write(f"{stock.get('shares', 0)}")
                
                with col4:
                    value = stock.get('price', 0) * stock.get('shares', 0)
                    st.write(f"${value:.2f}")
                
                with col5:
                    if st.button("Remove", key=f"remove_{idx}"):
                        portfolio_id = st.session_state.current_portfolio.get('_id')
                        if portfolio_id and portfolio_id != 'temp_id':
                            success, message = remove_stock_from_portfolio(portfolio_id, stock['symbol'])
                            if success:
                                st.success(f"Removed {stock['symbol']} from portfolio")
                                st.rerun()
                            else:
                                st.error(f"Failed to remove: {message}")
                        else:
                            st.session_state.current_portfolio['stocks'].pop(idx)
                            st.rerun()
                
                st.markdown("---")
    
    else:

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Add Your First Stock", type="primary", use_container_width=True):
                go_to("stock_search")

    if st.session_state.get("show_my_stocks_analytics", False):
        st.divider()
        st.subheader("Portfolio Analytics & Predictions")

        if portfolio and portfolio.get('stocks'):
            all_stocks = portfolio['stocks']

            st.subheader("Overall Portfolio Value Prediction")

            total_current_value = 0
            total_predicted_value = 0
            portfolio_predictions = []

            for stock in all_stocks:
                try:
                    ticker = yf.Ticker(stock['symbol'])
                    hist_data = ticker.history(period="2y")

                    if not hist_data.empty and len(hist_data) >= 30:
                        price_data = hist_data['Close'].dropna()

                        prediction = calculate_stock_prediction(price_data, future_days=365)

                        if prediction:
                            current_price = prediction['current_price']
                            predicted_price = prediction['predicted_price']
                            shares = stock.get('shares', 1)

                            current_stock_value = current_price * shares
                            predicted_stock_value = predicted_price * shares

                            total_current_value += current_stock_value
                            total_predicted_value += predicted_stock_value

                            portfolio_predictions.append({
                                'symbol': stock['symbol'],
                                'name': stock.get('name', stock['symbol']),
                                'shares': shares,
                                'current_price': current_price,
                                'predicted_price': predicted_price,
                                'current_value': current_stock_value,
                                'predicted_value': predicted_stock_value,
                                'prediction': prediction
                            })
                except Exception as e:
                    st.warning(f"Could not analyze {stock['symbol']}: {str(e)}")
                    continue

            if portfolio_predictions:
                value_change = total_predicted_value - total_current_value
                value_change_pct = (value_change / total_current_value * 100) if total_current_value > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Portfolio Value", f"${total_current_value:,.2f}")
                with col2:
                    st.metric("Predicted Value (1 Year)", f"${total_predicted_value:,.2f}", f"{value_change:+,.2f} ({value_change_pct:+.2f}%)")
                with col3:
                    trend = "Upward" if value_change > 0 else "Downward"
                    st.metric("Trend", trend)

                st.divider()

                st.subheader("Individual Stock Predictions")

                for pred in portfolio_predictions:
                    with st.expander(f"{pred['symbol']} - {pred['name']}", expanded=False):
                        stock_change = pred['predicted_price'] - pred['current_price']
                        stock_change_pct = (stock_change / pred['current_price'] * 100) if pred['current_price'] > 0 else 0

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Current Price", f"${pred['current_price']:.2f}")
                        with col2:
                            st.metric("Predicted Price (1 Year)", f"${pred['predicted_price']:.2f}", f"{stock_change:+.2f} ({stock_change_pct:+.2f}%)")
                        with col3:
                            st.metric("Total Value Change", f"${pred['predicted_value'] - pred['current_value']:+,.2f}")

                        st.write("**Price Prediction Chart**")

                        if 'prediction' in pred:
                            st.line_chart(pd.DataFrame({
                                'Predicted Price': pred['prediction']['future_predictions']
                            }), height=300)
            else:
                st.warning("Could not generate predictions. Make sure your stocks have sufficient historical data.")
        else:

        if st.button("Hide Analytics"):
            st.session_state.show_my_stocks_analytics = False
            st.rerun()

def show_stock_historical_data(symbol, name):
    st.subheader(f"Historical Analysis: {symbol}")
    
    stock_info = get_stock_info_with_history(symbol)

    if stock_info and not stock_info['historical_data'].empty:
        historical_data = stock_info['historical_data']

        if 'price' in stock_info:
            st.metric("Current Price", f"${stock_info['price']:.2f}")
        if 'change' in stock_info:
            change_pct = (stock_info['change'] / stock_info['previous_price'] * 100) if stock_info.get('previous_price', 0) > 0 else 0
            st.metric("Daily Change", f"${stock_info['change']:+.2f}", f"{change_pct:+.2f}%")
        st.write(f"**Sector:** {stock_info.get('sector', 'N/A')}")
        st.write(f"**Industry:** {stock_info.get('industry', 'N/A')}")

        st.divider()

        if len(historical_data) > 0:
            first_price = historical_data['Close'].iloc[0]
            last_price = historical_data['Close'].iloc[-1]
            total_return = ((last_price - first_price) / first_price) * 100
            years = len(historical_data) / 252  # Approximate trading days per year
            annualized_return = ((last_price / first_price) ** (1/years) - 1) * 100 if years > 0 else 0

            st.metric("Total Return", f"{total_return:+.2f}%")
            st.metric("Annualized Return", f"{annualized_return:+.2f}%")
            st.metric("All-Time High", f"${historical_data['High'].max():.2f}")
            st.metric("All-Time Low", f"${historical_data['Low'].min():.2f}")

            st.divider()

            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Price History", "Volume", "Returns", "Statistics", "Prediction"])

            with tab1:
                st.subheader("Stock Price Over Time")
                timeframe = st.selectbox(
                    "Select Timeframe",
                    ["All Time", "Last 10 Years", "Last 5 Years", "Last 2 Years"],
                    key=f"timeframe_{symbol}"
                )

                if timeframe == "All Time":
                    chart_data = historical_data
                elif timeframe == "Last 10 Years":
                    chart_data = historical_data.tail(10 * 252)
                elif timeframe == "Last 5 Years":
                    chart_data = historical_data.tail(5 * 252)
                else:  # Last 2 Years
                    chart_data = historical_data.tail(2 * 252)

                st.line_chart(chart_data['Close'], height=400)

                st.subheader("OHLC Data")
                st.write("**Open Prices**")
                st.line_chart(chart_data['Open'], height=150)
                st.write("**High Prices**")
                st.line_chart(chart_data['High'], height=150)
                st.write("**Low Prices**")
                st.line_chart(chart_data['Low'], height=150)
                st.write("**Close Prices**")
                st.line_chart(chart_data['Close'], height=150)

            with tab2:
                st.subheader("Trading Volume Over Time")
                st.bar_chart(chart_data['Volume'], height=400)

                avg_volume = chart_data['Volume'].mean()
                max_volume = chart_data['Volume'].max()
                st.metric("Average Volume", f"{avg_volume:,.0f}")
                st.metric("Maximum Volume", f"{max_volume:,.0f}")

            with tab3:
                st.subheader("Daily Returns Analysis")
                returns = chart_data['Close'].pct_change().dropna()

                st.line_chart(returns * 100, height=300)

                st.metric("Avg Daily Return", f"{returns.mean() * 100:.2f}%")
                st.metric("Volatility", f"{returns.std() * 100:.2f}%")
                st.metric("Best Day", f"{returns.max() * 100:.2f}%")
                st.metric("Worst Day", f"{returns.min() * 100:.2f}%")

            with tab4:
                st.subheader("Detailed Statistics")

                stats_data = {
                    "Metric": ["Current Price", "52-Week High", "52-Week Low", "All-Time High", "All-Time Low",
                             "Total Return", "Annualized Return", "Volatility", "Average Volume", "Market Cap"],
                    "Value": []
                }

                recent_year = historical_data.tail(252) if len(historical_data) > 252 else historical_data
                fifty_two_week_high = recent_year['High'].max()
                fifty_two_week_low = recent_year['Low'].min()

                stats_data["Value"] = [
                    f"${stock_info.get('price', last_price):.2f}",
                    f"${fifty_two_week_high:.2f}",
                    f"${fifty_two_week_low:.2f}",
                    f"${historical_data['High'].max():.2f}",
                    f"${historical_data['Low'].min():.2f}",
                    f"{total_return:+.2f}%",
                    f"{annualized_return:+.2f}%",
                    f"{returns.std() * 100:.2f}%",
                    f"{historical_data['Volume'].mean():,.0f}",
                    f"${stock_info.get('info', {}).get('marketCap', 'N/A')}"
                ]

                stats_df = pd.DataFrame(stats_data)
                st.dataframe(stats_df, use_container_width=True)

                if stock_info.get('info'):
                    st.subheader("Company Information")
                    info = stock_info['info']

                    st.write(f"**Country:** {info.get('country', 'N/A')}")
                    st.write(f"**Employees:** {info.get('fullTimeEmployees', 'N/A')}")
                    st.write(f"**Website:** {info.get('website', 'N/A')}")
                    st.write(f"**P/E Ratio:** {info.get('trailingPE', 'N/A')}")
                    st.write(f"**Dividend Yield:** {info.get('dividendYield', 'N/A')}")
                    st.write(f"**Beta:** {info.get('beta', 'N/A')}")

                    if info.get('longBusinessSummary'):
                        st.subheader("Business Summary")
                        st.write(info['longBusinessSummary'])

            with tab5:
                st.subheader("Price Prediction Using Linear Regression")

                data = historical_data['Close'].dropna()

                if len(data) >= 30:  # Need at least 30 days of data
                    prediction = calculate_stock_prediction(data, future_days=365)

                    if prediction:
                        current_price = prediction['current_price']
                        predicted_1year = prediction['predicted_price']
                        predicted_change = predicted_1year - current_price
                        predicted_change_pct = (predicted_change / current_price) * 100

                        st.metric("Current Price", f"${current_price:.2f}")
                        st.metric("Predicted Price (1 Year)", f"${predicted_1year:.2f}", f"{predicted_change:+.2f} ({predicted_change_pct:+.2f}%)")
                        st.metric("Model R² Score", f"{prediction['r_squared']:.4f}")

                        st.divider()

                        historical_dates = data.index

                        last_date = historical_dates[-1]
                        future_dates = pd.date_range(start=last_date + timedelta(days=1),
                                                     periods=365, freq='D')

                        st.subheader("Historical Data with Regression Line")

                        historical_chart_data = pd.DataFrame({
                            'Actual Price': data.values,
                            'Regression Line': prediction['y_pred']
                        }, index=historical_dates)

                        st.line_chart(historical_chart_data, height=400)

                        st.subheader("Future Price Prediction (Next Year)")

                        lookback_days = min(504, len(data))  # 2 years or less
                        recent_data = data.tail(lookback_days)
                        recent_dates = recent_data.index
                        recent_X = np.arange(len(data) - lookback_days, len(data))
                        recent_pred = prediction['slope'] * recent_X + prediction['intercept']

                        combined_dates = list(recent_dates) + list(future_dates)
                        combined_actual = list(recent_data.values) + [None] * 365
                        combined_predicted = list(recent_pred) + list(prediction['future_predictions'])

                        combined_df = pd.DataFrame({
                            'Historical Price': combined_actual,
                            'Predicted Price': [None] * lookback_days + list(prediction['future_predictions'])
                        }, index=combined_dates)

                        st.line_chart(combined_df, height=400)

                        st.divider()
                        st.subheader("Model Details")
                        st.write(f"**Regression Equation:** Price = {prediction['slope']:.4f} × Days + {prediction['intercept']:.2f}")
                        st.write(f"**Daily Trend:** {'Upward' if prediction['slope'] > 0 else 'Downward'} (${prediction['slope']:.4f} per day)")
                        st.write(f"**Training Data Points:** {len(data)} days")
                        st.write(f"**Prediction Period:** 365 days (1 year)")
                else:
                    st.warning("Not enough historical data for regression analysis. Need at least 30 days.")
    else:
        st.error(f"No historical data available for {symbol}")

def stock_search_page(go_to, get_user_info, change_password):
    with st.sidebar:
        st.header("Stock Search")
        
        st.subheader("Filters")
        
        available_countries = ["All", "United States", "United Kingdom", "Australia", "Hong Kong", "China"]
        if 'current_portfolio' in st.session_state:
            portfolio_countries = st.session_state.current_portfolio.get('countries', [])
            country_options = ["All"] + portfolio_countries + [c for c in available_countries[1:] if c not in portfolio_countries]
        else:
            country_options = available_countries
            
        selected_country = st.selectbox("Country", country_options)
        
        st.divider()
        
        if st.button("← Back to My Stocks", use_container_width=True):
            go_to("my_stocks")
        
        if st.button("Dashboard", use_container_width=True):
            go_to("dashboard")
    
    st.title("Stock Search")
    st.markdown("### Find and add stocks to your portfolio")

    if 'current_portfolio' in st.session_state:
        portfolio_name = st.session_state.current_portfolio.get('name', 'Unknown')
        portfolio_id = st.session_state.current_portfolio.get('_id', 'None')
    else:
        st.warning("No portfolio selected. Please select a portfolio first.")
        if st.button("Go to Portfolios"):
            go_to("portfolios")
        st.stop()
    
    search_query = st.text_input("Search for stocks (symbol or company name)", placeholder="e.g., AAPL, Apple, Tesla")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        search_button = st.button("Search", type="primary")
    
    st.divider()
    
    if search_query or search_button:
        st.subheader(f"Search Results for '{search_query or 'Popular Stocks'}'")
        
        if selected_country != "All":
            all_stocks = get_stocks_for_search(selected_country)
        else:
            all_stocks = []
            for country in STOCK_SYMBOLS_BY_COUNTRY.keys():
                country_stocks = get_stocks_for_search(country)
                all_stocks.extend(country_stocks)

        if search_query:
            filtered_stocks = [s for s in all_stocks 
                             if search_query.upper() in s["symbol"] or 
                                search_query.lower() in s["name"].lower()]
        else:
            filtered_stocks = all_stocks
        
        if selected_country != "All":
        else:
        
        for stock in filtered_stocks:
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 1.5, 1.5, 2, 1])
                
                with col1:
                    st.write(f"**{stock['symbol']}**")
                
                with col2:
                    st.write(f"{stock['country']}")
                
                with col3:
                    st.write(f"${stock['price']:.2f}")
                
                with col4:
                    change_color = "+" if stock['change'] > 0 else "-"
                    st.write(f"{change_color} {stock['change']:+.2f}")
                
                with col5:
                    with st.form(key=f"add_form_{stock['symbol']}"):
                        shares = st.number_input(
                            "Shares",
                            min_value=1,
                            max_value=10000,
                            value=1,
                            help="Number of shares you purchased"
                        )

                        purchase_price = st.number_input(
                            "Purchase Price/Share ($)",
                            min_value=0.01,
                            max_value=100000.0,
                            value=float(stock['price']),
                            step=0.01,
                            help="Price you paid per share"
                        )

                        total_cost = purchase_price * shares

                        submitted = st.form_submit_button("Add", use_container_width=True)

                        if submitted:
                            if 'current_portfolio' not in st.session_state:
                                st.session_state.current_portfolio = {'stocks': []}

                            existing = [s for s in st.session_state.current_portfolio.get('stocks', [])
                                      if s['symbol'] == stock['symbol']]

                            if existing:
                                st.warning(f"{stock['symbol']} is already in your portfolio!")
                            else:
                                new_stock = {
                                    'symbol': stock['symbol'],
                                    'name': stock['name'],
                                    'purchase_price': purchase_price,
                                    'current_price': stock['price'],
                                    'price': purchase_price,
                                    'shares': shares,
                                    'purchase_value': total_cost
                                }

                                if 'stocks' not in st.session_state.current_portfolio:
                                    st.session_state.current_portfolio['stocks'] = []

                                st.session_state.current_portfolio['stocks'].append(new_stock)

                                portfolio_id = st.session_state.current_portfolio.get('_id')

                                if portfolio_id and portfolio_id != 'temp_id':
                                    try:
                                        db_success, db_message = add_stock_to_portfolio(portfolio_id, new_stock)

                                        if db_success:
                                            st.success(f"Successfully added {shares} shares of {stock['symbol']} at ${purchase_price:.2f}/share to your portfolio!")
                                        else:
                                            st.error(f"Failed to save: {db_message}")
                                            st.session_state.current_portfolio['stocks'].pop()
                                    except Exception as e:
                                        st.error(f"Error adding stock: {str(e)}")
                                        st.session_state.current_portfolio['stocks'].pop()
                                else:
                                    st.error(f"No portfolio selected. Please select a portfolio first.")
                                    st.session_state.current_portfolio['stocks'].pop()

                with col6:
                    if st.button("History", key=f"history_{stock['symbol']}"):
                        show_stock_historical_data(stock['symbol'], stock['name'])
                
                st.markdown("---")
        
        if not filtered_stocks:
    
    else:

def edit_portfolio_page(go_to, get_user_info, change_password):
    if 'edit_portfolio_id' not in st.session_state:
        st.error("No portfolio selected for editing")
        go_to("portfolios")
        return

    portfolio_id = st.session_state.edit_portfolio_id
    portfolio = get_portfolio_by_id(portfolio_id)
    
    if not portfolio:
        st.error("Portfolio not found")
        go_to("portfolios")
        return
    
    with st.sidebar:
        st.header("Edit Portfolio")
        
        st.write(f"**Portfolio:** {portfolio['portfolio_name']}")
        
        st.divider()
        
        st.subheader("Actions")
        
        if st.button(" Add More Stocks", use_container_width=True, type="primary"):
            st.session_state.current_portfolio = {
                '_id': portfolio_id,
                'name': portfolio['portfolio_name'],
                'countries': portfolio['countries'],
                'stocks': portfolio.get('stocks', [])
            }
            go_to("stock_search")
        
        st.divider()
        
        if st.button("← Back to Portfolios", use_container_width=True):
            go_to("portfolios")
        
        if st.button("Dashboard", use_container_width=True):
            go_to("dashboard")
    
    st.title("Edit Portfolio")
    
    st.subheader("Portfolio Information")
    
    col_name, col_name_btn = st.columns([3, 1])
    with col_name:
        if st.session_state.get('editing_portfolio_name'):
            new_portfolio_name = st.text_input(
                "Portfolio Name",
                value=portfolio['portfolio_name'],
                key="portfolio_name_input",
                help="Enter the new name for your portfolio"
            )
        else:
            st.markdown(f"**Current Name:** {portfolio['portfolio_name']}")
    
    with col_name_btn:
        st.write("") # Spacing
        if st.session_state.get('editing_portfolio_name'):
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("Save", key="save_name"):
                    if 'portfolio_name_input' in st.session_state and st.session_state.portfolio_name_input.strip():
                        success, message = update_portfolio(portfolio_id, {'portfolio_name': st.session_state.portfolio_name_input.strip()})
                        
                        if success:
                            st.success(f"Portfolio name updated to '{st.session_state.portfolio_name_input}'!")
                            st.session_state.editing_portfolio_name = False
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"Failed to update name: {message}")
                    else:
                        st.error("Please enter a valid portfolio name")
            
            with col_cancel:
                if st.button("Cancel", key="cancel_name"):
                    st.session_state.editing_portfolio_name = False
                    st.rerun()
        else:
            if st.button("Edit Name", key="edit_name"):
                st.session_state.editing_portfolio_name = True
                st.rerun()
    
    st.divider()
    
    st.subheader("Portfolio Summary")
    total_value = sum(stock.get('price', 0) * stock.get('shares', 1) for stock in portfolio.get('stocks', []))
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Value", f"${total_value:.2f}")
    with col2:
        st.metric("Number of Stocks", len(portfolio.get('stocks', [])))
    
    st.divider()
    
    st.subheader("Manage Stocks")
    
    if portfolio.get('stocks'):
        stocks = portfolio['stocks']
        
        if 'stock_changes' not in st.session_state:
            st.session_state.stock_changes = {}
        
        updated_stocks = []
        stocks_to_remove = []
        
        for idx, stock in enumerate(stocks):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1.5, 1])
                
                with col1:
                    st.write(f"**{stock['symbol']}**")
                
                with col2:
                    st.write(f"${stock.get('price', 0):.2f}")
                
                with col3:
                    current_shares = stock.get('shares', 1)
                    new_shares = st.number_input(
                        "Shares",
                        min_value=0,
                        max_value=10000,
                        value=current_shares,
                        key=f"shares_{stock['symbol']}_{idx}",
                        help="Set to 0 to remove stock"
                    )
                    
                    if new_shares != current_shares:
                        st.session_state.stock_changes[stock['symbol']] = new_shares
                
                with col4:
                    shares_to_use = st.session_state.stock_changes.get(stock['symbol'], current_shares)
                    total_stock_value = stock.get('price', 0) * shares_to_use
                    st.write(f"${total_stock_value:.2f}")
                
                with col5:
                    if st.button("Remove", key=f"remove_{stock['symbol']}_{idx}"):
                        st.session_state.stock_changes[stock['symbol']] = 0
                
                final_shares = st.session_state.stock_changes.get(stock['symbol'], current_shares)
                if final_shares > 0:
                    updated_stock = stock.copy()
                    updated_stock['shares'] = final_shares
                    updated_stock['value'] = stock.get('price', 0) * final_shares
                    updated_stocks.append(updated_stock)
                
                st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Changes", type="primary", use_container_width=True):
                final_stocks = [s for s in updated_stocks if s['shares'] > 0]
                
                for symbol in stocks_to_remove:
                    success, message = remove_stock_from_portfolio(portfolio_id, symbol)
                    if success:
                        st.success(f"Removed {symbol}")
                    else:
                        st.error(f"Failed to remove {symbol}: {message}")
                
                update_data = {'stocks': final_stocks}
                success, message = update_portfolio(portfolio_id, update_data)
                
                if success:
                    st.success("Portfolio updated successfully!")
                    st.session_state.stock_changes = {}  # Clear changes
                    st.balloons()
                else:
                    st.error(f"Failed to update portfolio: {message}")
        
        with col2:
            if st.button("Cancel Changes", use_container_width=True):
                st.session_state.stock_changes = {}  # Clear changes
    
    else:
        
        if st.button("Add Your First Stock", type="primary", use_container_width=True):
            st.session_state.current_portfolio = {
                '_id': portfolio_id,
                'name': portfolio['portfolio_name'],
                'countries': portfolio['countries'],
                'stocks': []
            }
            go_to("stock_search")

def portfolio_details_page(go_to, get_user_info, change_password):
    """Render detailed portfolio view with stock performance analysis"""
    
    if 'view_portfolio_id' not in st.session_state:
        st.error("No portfolio selected for viewing")
        go_to("portfolios")
        return
    
    portfolio_id = st.session_state.view_portfolio_id
    portfolio = get_portfolio_by_id(portfolio_id)
    
    if not portfolio:
        st.error("Portfolio not found")
        go_to("portfolios")
        return
    
    with st.sidebar:
        st.header("Portfolio Details")
        
        st.write(f"**Portfolio:** {portfolio['portfolio_name']}")
        st.write(f"**Created:** {portfolio['created_at'].strftime('%Y-%m-%d') if portfolio.get('created_at') else 'Unknown'}")
        
        st.divider()
        
        st.subheader("Actions")
        
        if st.button("Edit Portfolio", use_container_width=True, type="primary"):
            st.session_state.edit_portfolio_id = portfolio_id
            st.session_state.edit_portfolio_name = portfolio['portfolio_name']
            go_to("edit_portfolio")

        if st.button(" Portfolio Analytics", use_container_width=True):
            st.session_state.analytics_portfolio_id = portfolio_id
            go_to("portfolio_analytics")

        st.divider()

        if st.button("← Back to Portfolios", use_container_width=True):
            go_to("portfolios")
        
        if st.button("Dashboard", use_container_width=True):
            go_to("dashboard")
    
    st.title("Portfolio Details")
    st.markdown(f"### {portfolio['portfolio_name']}")
    
    stocks = portfolio.get('stocks', [])
    
    if not stocks:
        if st.button("Add Stocks", type="primary"):
            st.session_state.current_portfolio = {
                '_id': portfolio_id,
                'name': portfolio['portfolio_name'],
                'countries': portfolio['countries'],
                'stocks': []
            }
            go_to("stock_search")
        return
    
    total_purchase_value = 0
    for stock in stocks:
        purchase_price = stock.get('purchase_price', stock.get('price', 0))
        shares = stock.get('shares', 1)
        total_purchase_value += purchase_price * shares
    
    current_stock_data = {}
    for stock in stocks:
        try:
            ticker = yf.Ticker(stock['symbol'])
            current_data = ticker.history(period="1d")
            if not current_data.empty:
                current_price = float(current_data['Close'].iloc[-1])
                current_stock_data[stock['symbol']] = current_price
        except Exception:
            stored_current = stock.get('current_price')
            if stored_current:
                current_stock_data[stock['symbol']] = stored_current

    current_total_value = 0
    for stock in stocks:
        symbol = stock['symbol']
        shares = stock.get('shares', 1)
        purchase_price = stock.get('purchase_price', stock.get('price', 0))
        current_price = current_stock_data.get(symbol) or stock.get('current_price') or purchase_price
        current_total_value += current_price * shares
    
    total_gain_loss = current_total_value - total_purchase_value
    total_gain_loss_pct = (total_gain_loss / total_purchase_value * 100) if total_purchase_value > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Purchase Value", f"${total_purchase_value:.2f}")
    with col2:
        st.metric("Current Value", f"${current_total_value:.2f}")
    with col3:
        st.markdown("**Total Gain/Loss**")
        st.markdown(f"${total_gain_loss:+.2f}")
        st.markdown(format_percentage_with_color(total_gain_loss_pct), unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("Stock Holdings Detail")
    
    stock_details = []
    for stock in stocks:
        symbol = stock['symbol']
        shares = stock.get('shares', 1)
        purchase_price = stock.get('purchase_price', stock.get('price', 0))
        current_price = current_stock_data.get(symbol) or stock.get('current_price') or purchase_price
        using_purchase_as_current = not (current_stock_data.get(symbol) or stock.get('current_price'))
        
        purchase_value = purchase_price * shares
        current_value = current_price * shares
        gain_loss = current_value - purchase_value
        gain_loss_pct = (gain_loss / purchase_value * 100) if purchase_value > 0 else 0
        
        current_price_display = f"${current_price:.2f}"
        if using_purchase_as_current:
            current_price_display += " (est.)"
        
        stock_details.append({
            'Symbol': symbol,
            'Company Name': stock.get('name', symbol),
            'Number of Shares': shares,
            'Average Purchase Price': f"${purchase_price:.2f}",
            'Purchase Value': f"${purchase_value:.2f}",
            'Current Average Price': current_price_display,
            'Current Value': f"${current_value:.2f}",
            'Percentage Change': format_percentage_with_color(gain_loss_pct),
            'Value Change': f"${gain_loss:+.2f}"
        })
    
    if stock_details:
        df = pd.DataFrame(stock_details)
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        st.divider()
        
        st.subheader("Individual Stock Performance")
        
        cols = st.columns(3)
        for idx, stock in enumerate(stocks):
            with cols[idx % 2]:
                symbol = stock['symbol']
                shares = stock.get('shares', 1)
                purchase_price = stock.get('purchase_price', stock.get('price', 0))
                current_price = current_stock_data.get(symbol) or stock.get('current_price') or purchase_price
                
                purchase_value = purchase_price * shares
                current_value = current_price * shares
                gain_loss = current_value - purchase_value
                gain_loss_pct = (gain_loss / purchase_value * 100) if purchase_value > 0 else 0
                
                with st.container():
                    st.markdown(f"#### {symbol}")
                    
                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric("Current Value", f"${current_value:.2f}", f"{gain_loss:+.2f}")
                    with metric_col2:
                        st.markdown("**Performance**")
                        st.markdown(format_percentage_with_color(gain_loss_pct), unsafe_allow_html=True)
                    
                    st.write(f"**Shares:** {shares}")
                    st.write(f"**Purchase Price:** ${purchase_price:.2f}")
                    st.write(f"**Current Price:** ${current_price:.2f}")
                    
                    button_col1, button_col2 = st.columns(2)
                    with button_col1:
                        if st.button("View History", key=f"portfolio_history_{symbol}_{idx}"):
                            show_stock_historical_data(symbol, stock.get('name', symbol))
                    
                    try:
                        ticker = yf.Ticker(symbol)
                        hist_data = ticker.history(period="1mo")
                        if not hist_data.empty:
                            st.line_chart(hist_data['Close'], height=200)
                    except Exception:
                    
                    st.markdown("---")

    else:
        st.warning("No stock details available")

    if st.session_state.get("show_portfolio_details_analytics", False):
        st.divider()
        st.subheader("Portfolio Analytics & Predictions")

        if stocks:
            st.subheader("Overall Portfolio Value Prediction")

            total_current_value = 0
            total_predicted_value = 0
            portfolio_predictions = []

            for stock in stocks:
                try:
                    ticker = yf.Ticker(stock['symbol'])
                    hist_data = ticker.history(period="2y")

                    if not hist_data.empty and len(hist_data) >= 30:
                        price_data = hist_data['Close'].dropna()

                        X = np.arange(len(price_data)).reshape(-1, 1)
                        y = price_data.values
                        coefficients = np.polyfit(X.flatten(), y, 1)
                        slope = coefficients[0]
                        intercept = coefficients[1]

                        future_days = 365
                        future_X = len(price_data) + future_days
                        predicted_price = slope * future_X + intercept

                        current_price = price_data.iloc[-1]
                        shares = stock.get('shares', 1)

                        current_stock_value = current_price * shares
                        predicted_stock_value = predicted_price * shares

                        total_current_value += current_stock_value
                        total_predicted_value += predicted_stock_value

                        portfolio_predictions.append({
                            'symbol': stock['symbol'],
                            'name': stock.get('name', stock['symbol']),
                            'shares': shares,
                            'current_price': current_price,
                            'predicted_price': predicted_price,
                            'current_value': current_stock_value,
                            'predicted_value': predicted_stock_value,
                            'slope': slope,
                            'historical_data': price_data
                        })
                except Exception as e:
                    st.warning(f"Could not analyze {stock['symbol']}: {str(e)}")
                    continue

            if portfolio_predictions:
                value_change = total_predicted_value - total_current_value
                value_change_pct = (value_change / total_current_value * 100) if total_current_value > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Portfolio Value", f"${total_current_value:,.2f}")
                with col2:
                    st.metric("Predicted Value (1 Year)", f"${total_predicted_value:,.2f}", f"{value_change:+,.2f} ({value_change_pct:+.2f}%)")
                with col3:
                    trend = "Upward" if value_change > 0 else "Downward"
                    st.metric("Trend", trend)

                st.divider()

                st.subheader("Individual Stock Predictions")

                for pred in portfolio_predictions:
                    with st.expander(f"{pred['symbol']} - {pred['name']}", expanded=False):
                        stock_change = pred['predicted_price'] - pred['current_price']
                        stock_change_pct = (stock_change / pred['current_price'] * 100) if pred['current_price'] > 0 else 0

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Current Price", f"${pred['current_price']:.2f}")
                        with col2:
                            st.metric("Predicted Price (1 Year)", f"${pred['predicted_price']:.2f}", f"{stock_change:+.2f} ({stock_change_pct:+.2f}%)")
                        with col3:
                            st.metric("Total Value Change", f"${pred['predicted_value'] - pred['current_value']:+,.2f}")

                        st.write("**Price Prediction Chart**")

                        if 'prediction' in pred:
                            st.line_chart(pd.DataFrame({
                                'Predicted Price': pred['prediction']['future_predictions']
                            }), height=300)
            else:
                st.warning("Could not generate predictions. Make sure your stocks have sufficient historical data.")
        else:

        if st.button("Hide Analytics"):
            st.session_state.show_portfolio_details_analytics = False
            st.rerun()

def portfolio_analytics_page(go_to, get_user_info, change_password):
    """Render portfolio analytics page with predictions"""

    with st.sidebar:
        st.header("Portfolio Analytics")

        st.divider()

        if st.button("← Back to Portfolios", use_container_width=True):
            go_to("portfolios")

        if st.button("Dashboard", use_container_width=True):
            go_to("dashboard")

        if st.button("Logout", use_container_width=True):
            handle_logout()

    st.title("Portfolio Analytics & Predictions")

    if 'analytics_portfolio_id' in st.session_state:
        portfolio_id = st.session_state.analytics_portfolio_id
        portfolio = get_portfolio_by_id(portfolio_id)

        if not portfolio:
            st.error("Portfolio not found")
            if st.button("Back to Portfolios"):
                go_to("portfolios")
            return

        st.markdown(f"### Analyzing: {portfolio['portfolio_name']}")
        stocks = portfolio.get('stocks', [])

    else:
        st.markdown("### Analyzing: All Portfolios")
        user_portfolios = get_user_portfolios(st.session_state.username)

        if not user_portfolios:
            return

        stocks = []
        for portfolio in user_portfolios:
            for stock in portfolio.get('stocks', []):
                stocks.append(stock)

    if not stocks:
        if st.button("Go to Stock Search"):
            go_to("stock_search")
        return

    st.subheader("Overall Portfolio Value Prediction")

    total_current_value = 0
    total_predicted_value = 0
    portfolio_predictions = []

    for stock in stocks:
        try:
            ticker = yf.Ticker(stock['symbol'])
            hist_data = ticker.history(period="2y")

            if not hist_data.empty and len(hist_data) >= 30:
                price_data = hist_data['Close'].dropna()

                X = np.arange(len(price_data)).reshape(-1, 1)
                y = price_data.values
                coefficients = np.polyfit(X.flatten(), y, 1)
                slope = coefficients[0]
                intercept = coefficients[1]

                future_days = 365
                future_X = len(price_data) + future_days
                predicted_price = slope * future_X + intercept

                current_price = price_data.iloc[-1]
                shares = stock.get('shares', 1)

                current_stock_value = current_price * shares
                predicted_stock_value = predicted_price * shares

                total_current_value += current_stock_value
                total_predicted_value += predicted_stock_value

                portfolio_predictions.append({
                    'symbol': stock['symbol'],
                    'name': stock.get('name', stock['symbol']),
                    'shares': shares,
                    'current_price': current_price,
                    'predicted_price': predicted_price,
                    'current_value': current_stock_value,
                    'predicted_value': predicted_stock_value,
                    'slope': slope,
                    'historical_data': price_data
                })
        except Exception as e:
            st.warning(f"Could not analyze {stock['symbol']}: {str(e)}")
            continue

    if portfolio_predictions:
        value_change = total_predicted_value - total_current_value
        value_change_pct = (value_change / total_current_value * 100) if total_current_value > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Portfolio Value", f"${total_current_value:,.2f}")
        with col2:
            st.metric("Predicted Value (1 Year)", f"${total_predicted_value:,.2f}", f"{value_change:+,.2f} ({value_change_pct:+.2f}%)")
        with col3:
            trend = "Upward" if value_change > 0 else "Downward"
            st.metric("Trend", trend)

        st.divider()

        st.subheader("Individual Stock Predictions")

        for pred in portfolio_predictions:
            with st.expander(f"{pred['symbol']} - {pred['name']}", expanded=False):
                stock_change = pred['predicted_price'] - pred['current_price']
                stock_change_pct = (stock_change / pred['current_price'] * 100) if pred['current_price'] > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Price", f"${pred['current_price']:.2f}")
                with col2:
                    st.metric("Predicted Price (1 Year)", f"${pred['predicted_price']:.2f}",
                             f"{stock_change:+.2f} ({stock_change_pct:+.2f}%)")
                with col3:
                    st.metric("Total Value Change", f"${pred['predicted_value'] - pred['current_value']:+,.2f}")

                st.write("**Price Prediction Chart**")

                lookback_days = min(365, len(pred['historical_data']))
                recent_data = pred['historical_data'].tail(lookback_days)
                recent_dates = recent_data.index

                last_date = recent_dates[-1]
                future_dates = pd.date_range(start=last_date + timedelta(days=1),
                                             periods=365, freq='D')

                future_X = np.arange(len(pred['historical_data']), len(pred['historical_data']) + 365)
                coefficients_full = np.polyfit(np.arange(len(pred['historical_data'])), pred['historical_data'].values, 1)
                future_predictions = coefficients_full[0] * future_X + coefficients_full[1]

                combined_dates = list(recent_dates) + list(future_dates)
                combined_actual = list(recent_data.values) + [None] * 365
                combined_predicted = [None] * lookback_days + list(future_predictions)

                chart_df = pd.DataFrame({
                    'Historical Price': combined_actual,
                    'Predicted Trend': combined_predicted
                }, index=combined_dates)

                st.line_chart(chart_df, height=300)
    else:
        st.warning("Could not generate predictions. Make sure your stocks have sufficient historical data.")

def media_portfolio_view_page(go_to, get_user_info, change_password):
    """Render read-only view of community portfolio"""
    import yfinance as yf

    if 'media_portfolio_id' not in st.session_state:
        st.error("No portfolio selected for viewing")
        go_to("dashboard")
        return

    portfolio_id = st.session_state.media_portfolio_id
    portfolio = get_portfolio_by_id(portfolio_id)

    if not portfolio:
        st.error("Portfolio not found")
        go_to("dashboard")
        return

    owner_username = st.session_state.get('media_portfolio_owner', portfolio.get('user_id', 'Unknown User'))

    with st.sidebar:
        st.header("Community Portfolio")

        st.write(f"**Owner:** {owner_username}")
        st.write(f"**Created:** {portfolio['created_at'].strftime('%Y-%m-%d') if portfolio.get('created_at') else 'Unknown'}")

        st.divider()

        if st.button("← Back to Dashboard", use_container_width=True):
            go_to("dashboard")

        if st.button("Logout", use_container_width=True):
            handle_logout()

    st.title(f"{owner_username}'s Portfolio")

    stocks = portfolio.get('stocks', [])

    if not stocks:
        return

    total_purchase_value = 0
    for stock in stocks:
        purchase_price = stock.get('purchase_price', stock.get('price', 0))
        shares = stock.get('shares', 1)
        total_purchase_value += purchase_price * shares

    current_stock_data = {}
    for stock in stocks:
        try:
            ticker = yf.Ticker(stock['symbol'])
            current_data = ticker.history(period="1d")
            if not current_data.empty:
                current_price = float(current_data['Close'].iloc[-1])
                current_stock_data[stock['symbol']] = current_price
        except Exception:
            stored_current = stock.get('current_price')
            if stored_current:
                current_stock_data[stock['symbol']] = stored_current

    current_total_value = 0
    for stock in stocks:
        symbol = stock['symbol']
        shares = stock.get('shares', 1)
        purchase_price = stock.get('purchase_price', stock.get('price', 0))
        current_price = current_stock_data.get(symbol) or stock.get('current_price') or purchase_price
        current_total_value += current_price * shares

    total_gain_loss = current_total_value - total_purchase_value
    total_gain_loss_pct = (total_gain_loss / total_purchase_value * 100) if total_purchase_value > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Purchase Value", f"${total_purchase_value:.2f}")
    with col2:
        st.metric("Current Value", f"${current_total_value:.2f}")
    with col3:
        st.markdown("**Total Gain/Loss**")
        st.markdown(f"${total_gain_loss:+.2f}")
        st.markdown(format_percentage_with_color(total_gain_loss_pct), unsafe_allow_html=True)

    st.divider()

    st.subheader("Stock Holdings Detail")

    stock_details = []
    for stock in stocks:
        symbol = stock['symbol']
        shares = stock.get('shares', 1)
        purchase_price = stock.get('purchase_price', stock.get('price', 0))
        current_price = current_stock_data.get(symbol) or stock.get('current_price') or purchase_price
        using_purchase_as_current = not (current_stock_data.get(symbol) or stock.get('current_price'))

        purchase_value = purchase_price * shares
        current_value = current_price * shares
        gain_loss = current_value - purchase_value
        gain_loss_pct = (gain_loss / purchase_value * 100) if purchase_value > 0 else 0

        current_price_display = f"${current_price:.2f}"
        if using_purchase_as_current:
            current_price_display += " (est.)"

        stock_details.append({
            'Symbol': symbol,
            'Company Name': stock.get('name', symbol),
            'Number of Shares': shares,
            'Average Purchase Price': f"${purchase_price:.2f}",
            'Purchase Value': f"${purchase_value:.2f}",
            'Current Average Price': current_price_display,
            'Current Value': f"${current_value:.2f}",
            'Percentage Change': format_percentage_with_color(gain_loss_pct),
            'Value Change': f"${gain_loss:+.2f}"
        })

    if stock_details:
        df = pd.DataFrame(stock_details)
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        st.divider()

        st.subheader("Individual Stock Performance")

        cols = st.columns(2)
        for idx, stock in enumerate(stocks):
            with cols[idx % 2]:
                symbol = stock['symbol']
                shares = stock.get('shares', 1)
                purchase_price = stock.get('purchase_price', stock.get('price', 0))
                current_price = current_stock_data.get(symbol) or stock.get('current_price') or purchase_price

                purchase_value = purchase_price * shares
                current_value = current_price * shares
                gain_loss = current_value - purchase_value
                gain_loss_pct = (gain_loss / purchase_value * 100) if purchase_value > 0 else 0

                with st.container():
                    st.markdown(f"#### {symbol}")

                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric("Current Value", f"${current_value:.2f}", f"{gain_loss:+.2f}")
                    with metric_col2:
                        st.markdown("**Performance**")
                        st.markdown(format_percentage_with_color(gain_loss_pct), unsafe_allow_html=True)

                    st.write(f"**Shares:** {shares}")
                    st.write(f"**Purchase Price:** ${purchase_price:.2f}")
                    st.write(f"**Current Price:** ${current_price:.2f}")

                    try:
                        ticker = yf.Ticker(symbol)
                        hist_data = ticker.history(period="1mo")
                        if not hist_data.empty:
                            st.line_chart(hist_data['Close'], height=200)
                    except Exception:

                    st.markdown("---")

    st.divider()
    st.subheader("Portfolio Prediction Analytics")

    total_current_value = 0
    total_predicted_value = 0
    portfolio_predictions = []

    for stock in stocks:
        try:
            ticker = yf.Ticker(stock['symbol'])
            hist_data = ticker.history(period="2y")

            if not hist_data.empty and len(hist_data) >= 30:
                price_data = hist_data['Close'].dropna()

                X = np.arange(len(price_data)).reshape(-1, 1)
                y = price_data.values
                coefficients = np.polyfit(X.flatten(), y, 1)
                slope = coefficients[0]
                intercept = coefficients[1]

                future_days = 365
                future_X = len(price_data) + future_days
                predicted_price = slope * future_X + intercept

                current_price = price_data.iloc[-1]
                shares = stock.get('shares', 1)

                current_stock_value = current_price * shares
                predicted_stock_value = predicted_price * shares

                total_current_value += current_stock_value
                total_predicted_value += predicted_stock_value

                portfolio_predictions.append({
                    'symbol': stock['symbol'],
                    'name': stock.get('name', stock['symbol']),
                    'shares': shares,
                    'current_price': current_price,
                    'predicted_price': predicted_price,
                    'current_value': current_stock_value,
                    'predicted_value': predicted_stock_value,
                    'slope': slope,
                    'historical_data': price_data
                })
        except Exception as e:
            st.warning(f"Could not analyze {stock['symbol']}: {str(e)}")
            continue

    if portfolio_predictions:
        value_change = total_predicted_value - total_current_value
        value_change_pct = (value_change / total_current_value * 100) if total_current_value > 0 else 0

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Portfolio Value", f"${total_current_value:,.2f}")
        with col2:
            st.metric("Predicted Value (1 Year)", f"${total_predicted_value:,.2f}", f"{value_change:+,.2f} ({value_change_pct:+.2f}%)")
        with col3:
            trend = "Upward" if value_change > 0 else "Downward"
            st.metric("Trend", trend)

        st.divider()

        st.subheader("Individual Stock Predictions")

        for pred in portfolio_predictions:
            with st.expander(f"{pred['symbol']} - {pred['name']}", expanded=False):
                stock_change = pred['predicted_price'] - pred['current_price']
                stock_change_pct = (stock_change / pred['current_price'] * 100) if pred['current_price'] > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Price", f"${pred['current_price']:.2f}")
                with col2:
                    st.metric("Predicted Price (1 Year)", f"${pred['predicted_price']:.2f}",
                             f"{stock_change:+.2f} ({stock_change_pct:+.2f}%)")
                with col3:
                    st.metric("Total Value Change", f"${pred['predicted_value'] - pred['current_value']:+,.2f}")

                st.write("**Price Prediction Chart**")

                lookback_days = min(365, len(pred['historical_data']))
                recent_data = pred['historical_data'].tail(lookback_days)
                recent_dates = recent_data.index

                last_date = recent_dates[-1]
                future_dates = pd.date_range(start=last_date + timedelta(days=1),
                                             periods=365, freq='D')

                future_X = np.arange(len(pred['historical_data']), len(pred['historical_data']) + 365)
                coefficients_full = np.polyfit(np.arange(len(pred['historical_data'])), pred['historical_data'].values, 1)
                future_predictions = coefficients_full[0] * future_X + coefficients_full[1]

                combined_dates = list(recent_dates) + list(future_dates)
                combined_actual = list(recent_data.values) + [None] * 365
                combined_predicted = [None] * lookback_days + list(future_predictions)

                chart_df = pd.DataFrame({
                    'Historical Price': combined_actual,
                    'Predicted Trend': combined_predicted
                }, index=combined_dates)

                st.line_chart(chart_df, height=300)
    else:
        st.warning("Could not generate predictions. Make sure the portfolio has stocks with sufficient historical data.")
