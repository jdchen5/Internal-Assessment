import streamlit as st
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
from urllib.parse import quote
from login import (
    get_user_portfolios, get_all_portfolios, get_portfolio_by_id,
    create_portfolio, update_portfolio, delete_portfolio,
    add_stock_to_portfolio, remove_stock_from_portfolio
)
from constants import STOCK_SYMBOLS_BY_COUNTRY, AVAILABLE_COUNTRIES

# ==================== UTILITY FUNCTIONS ====================

def handle_logout():
    """Reset session state and return user to login page."""
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.page = "login"
    st.rerun()

def format_percentage_with_color(percentage):
    """Format percentage with CSS class for color coding."""
    if percentage > 0:
        return f'<span class="positive-percentage">{percentage:+.2f}%</span>'
    elif percentage < 0:
        return f'<span class="negative-percentage">{percentage:+.2f}%</span>'
    return f'<span class="neutral-percentage">{percentage:.2f}%</span>'

def calculate_portfolio_value(stocks):
    """Calculate total value of a portfolio using purchase price × shares."""
    return sum(stock.get('purchase_price', stock.get('price', 0)) * stock.get('shares', 1) for stock in stocks)

def get_company_news_link(symbol):
    """Generate Google News search URL for a given stock symbol."""
    try:
        ticker = yf.Ticker(symbol)
        company_name = ticker.info.get('longName', symbol)
    except:
        company_name = symbol
    search_query = f"{company_name} {symbol} stock"
    return {
        'company_name': company_name,
        'symbol': symbol,
        'news_url': f"https://news.google.com/search?q={quote(search_query)}&hl=en-US&gl=US&ceid=US:en"
    }

# ==================== DATA FETCHING FUNCTIONS====================

@st.cache_data(ttl=86400)
def get_stock_data(symbol, days):
    """Fetch stock historical data for the past N days."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        return data
    
    except Exception as e:
        st.error(f"Failed to fetch data for {symbol}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_historical_stock_data(symbol, start_year=2000):
    """Fetch long-term historical stock data (default from year 2000)."""
    try:
        data = yf.download(symbol, start=datetime(start_year, 1, 1), end=datetime.now(), progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        return data
    except Exception as e:
        st.error(f"Failed to fetch historical data for {symbol}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_stocks_for_search(country):
    """Retrieve snapshot (price + name + 1-day change) for all stocks in a country."""

    if country not in STOCK_SYMBOLS_BY_COUNTRY:
        return []
    
    symbols = STOCK_SYMBOLS_BY_COUNTRY[country]
    stock_data = []
    
    try:
        for i in range(0, len(symbols), 10):
            batch = symbols[i:i + 10]
            tickers = yf.Tickers(" ".join(batch))
            for symbol in batch:
                try:
                    ticker = tickers.tickers[symbol]
                    hist = ticker.history(period="2d")
                    if not hist.empty and len(hist) >= 2:
                        current_price = float(hist['Close'].iloc[-1])
                        previous_price = float(hist['Close'].iloc[-2])
                        stock_data.append({
                            "symbol": symbol,
                            "name": ticker.info.get('longName', ticker.info.get('shortName', symbol)),
                            "price": current_price,
                            "change": current_price - previous_price,
                            "country": country
                        })
                except:
                    continue
    except Exception as e:
        st.error(f"Error fetching stock data: {str(e)}")
    return stock_data

@st.cache_data(ttl=86400)
def get_multiple_stocks_data(symbols, days):
    """Fetch data for multiple symbols and return {symbol: DataFrame}."""
    stock_data = {}
    for symbol in symbols:
        try:
            data = get_stock_data(symbol, days)
            if isinstance(data, pd.DataFrame) and not data.empty:
                stock_data[symbol] = data
        except:
            continue
    return stock_data

# ==================== PREDICTION & ANALYTICS ====================

def calculate_stock_prediction(price_data, future_days=365):
    """Perform simple linear regression to estimate future price trend."""
    if len(price_data) < 30:
        return None
    X = np.arange(len(price_data))
    y = price_data.values
    coefficients = np.polyfit(X, y, 1)

    # Fit linear regression line
    slope, intercept = coefficients[0], coefficients[1]

    # Predicted trend line
    y_pred = slope * X + intercept

    # Future projections
    future_X = np.arange(len(price_data), len(price_data) + future_days)
    future_predictions = slope * future_X + intercept

    # R² model accuracy score
    residuals = y - y_pred
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {
        'slope': slope, 'intercept': intercept, 'predicted_price': future_predictions[-1],
        'y_pred': y_pred, 'future_predictions': future_predictions, 'future_X': future_X,
        'r_squared': r_squared, 'current_price': price_data.iloc[-1]
    }

def get_portfolio_predictions(stocks):
    """Run prediction model for each stock and sum total projected future value."""
    total_current_value = 0
    total_predicted_value = 0
    predictions = []

    for stock in stocks:
        try:
            ticker = yf.Ticker(stock['symbol'])
            hist_data = ticker.history(period="2y")

            # Require minimum historical data
            if not hist_data.empty and len(hist_data) >= 30:
                price_data = hist_data['Close'].dropna()
                prediction = calculate_stock_prediction(price_data, 365)
                if prediction:
                    shares = stock.get('shares', 1)
                    current_value = prediction['current_price'] * shares
                    predicted_value = prediction['predicted_price'] * shares
                    total_current_value += current_value
                    total_predicted_value += predicted_value
                    predictions.append({
                        'symbol': stock['symbol'], 'name': stock.get('name', stock['symbol']),
                        'shares': shares, 'current_price': prediction['current_price'],
                        'predicted_price': prediction['predicted_price'],
                        'current_value': current_value, 'predicted_value': predicted_value,
                        'prediction': prediction
                    })
        except:
            continue
    return total_current_value, total_predicted_value, predictions

def display_portfolio_predictions(stocks):
    """Render full portfolio prediction summary + individual stock forecasts."""
    st.subheader("Portfolio Value Prediction")
    total_current, total_predicted, predictions = get_portfolio_predictions(stocks)
    
    if predictions:
        value_change = total_predicted - total_current
        value_change_pct = (value_change / total_current * 100) if total_current > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Value", f"${total_current:,.2f}")
        with col2:
            st.metric("Predicted (1Y)", f"${total_predicted:,.2f}", f"{value_change:+,.2f} ({value_change_pct:+.2f}%)")
        with col3:
            st.metric("Trend", "Upward" if value_change > 0 else "Downward")
        
        st.divider()
        st.subheader("Individual Stock Predictions")
        
        for pred in predictions:
            with st.expander(f"{pred['symbol']} - {pred['name']}", expanded=False):
                stock_change = pred['predicted_price'] - pred['current_price']
                stock_change_pct = (stock_change / pred['current_price'] * 100) if pred['current_price'] > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Price", f"${pred['current_price']:.2f}")
                with col2:
                    st.metric("Predicted (1Y)", f"${pred['predicted_price']:.2f}", f"{stock_change:+.2f} ({stock_change_pct:+.2f}%)")
                with col3:
                    st.metric("Value Change", f"${pred['predicted_value'] - pred['current_value']:+,.2f}")
                
                if 'prediction' in pred:
                    st.line_chart(pd.DataFrame({'Predicted Price': pred['prediction']['future_predictions']}), height=300)
    else:
        st.warning("Could not generate predictions. Ensure stocks have sufficient historical data.")

# ==================== UI COMPONENTS AND SIDEBAR RENDERING ====================

def render_sidebar(page_title, actions=None, back_button=None):
    """Render a dynamic sidebar with page title, action buttons, navigation, and logout."""
    with st.sidebar:
        st.header(page_title)

        # Render action buttons if provided
        if actions:
            st.subheader("Actions")
            for action in actions:
                if st.button(action['label'], use_container_width=True, type=action.get('type', 'secondary'), key=action.get('key')):
                    action['callback']()
        st.divider()

        # Optional back button
        if back_button:
            if st.button(f"← {back_button['label']}", use_container_width=True):
                back_button['callback']()

        # Navigation buttons
        if st.button("Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button("Logout", use_container_width=True):
            handle_logout()

@st.dialog("Delete Portfolio")
def show_delete_confirmation_popup():
    """Popup dialog confirming portfolio deletion."""
    portfolio_id = st.session_state.get('confirm_delete_portfolio')
    portfolio_name = st.session_state.get('confirm_delete_name', 'Unknown Portfolio')
    st.warning(f"**Confirm Deletion**")
    st.write(f"Are you sure you want to delete **{portfolio_name}**? This action cannot be undone.")
    col1, col2 = st.columns(2)
    with col1:
        # Confirm deletion
        if st.button("Yes, Delete", type="primary", use_container_width=True):
            success, message = delete_portfolio(portfolio_id, st.session_state.username)
            if success:
                st.success(f"Portfolio '{portfolio_name}' deleted!")
                del st.session_state.confirm_delete_portfolio
                del st.session_state.confirm_delete_name
                st.rerun()
            else:
                st.error(f"Failed: {message}")
    with col2:
        # Cancel deletion
        if st.button("Cancel", use_container_width=True):
            del st.session_state.confirm_delete_portfolio
            del st.session_state.confirm_delete_name
            st.rerun()

def display_stock_metrics(data, symbol):
    """Show stock KPIs: current price, change %, 52-week range, volume."""
    if isinstance(data, pd.DataFrame) and not data.empty:
        latest = data.iloc[-1]
        previous = data.iloc[-2] if len(data) > 1 else latest

         # Daily price movement
        change = float(latest["Close"]) - float(previous["Close"])
        change_pct = (change / float(previous["Close"])) * 100 if float(previous["Close"]) != 0 else 0
        
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
                st.metric("Volume", f"{int(float(latest['Volume'])):,}")
            except:
                st.metric("Volume", "N/A")

def display_stock_chart(data, show_volume=True, show_moving_avg=False):
    """Render price line-chart and optional volume or high-low chart."""
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Price Chart")
        chart_data = pd.DataFrame({'Close': data['Close']})
        if show_moving_avg and len(data) >= 20:
            chart_data['20-Day MA'] = data['Close'].rolling(window=20).mean()
        st.line_chart(chart_data, height=400)
    with col2:
        if show_volume and 'Volume' in data.columns:
            st.subheader("Volume Chart")
            st.bar_chart(pd.DataFrame({'Volume': data['Volume']}), height=400)
        elif 'High' in data.columns and 'Low' in data.columns:
            st.subheader("High-Low Range")
            st.line_chart(pd.DataFrame({'High': data['High'], 'Low': data['Low']}), height=400)

# ==================== LOGIN PAGE FUNCTIONS ====================

def login_page(go_to, verify_user, update_last_login):
    """Render login screen and authenticate user."""
    st.title("Login")

     # User inputs
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", type="primary", use_container_width=True):
            # Validate input
            if not username or not password:
                st.error("Please enter both username and password")

            # Verify credentials
            elif verify_user(username, password):
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

# ==================== REGISTRATION PAGE FUNCTIONS ====================
def register_page(go_to, register_user):
    """Allow new users to register an account."""
    st.title("Register")

    # Registration fields
    username = st.text_input("Choose a username")
    email = st.text_input("Email")
    password = st.text_input("Choose a password", type="password",
        help="Must be at least 8 characters with uppercase, lowercase, number and special character")
    confirm_password = st.text_input("Confirm password", type="password")
    
    # Check password match
    if password and confirm_password:
        st.success("Passwords match") if password == confirm_password else st.error("Passwords don't match")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Register", type="primary", use_container_width=True):
            success, message = register_user(username, password, email)
            if success:
                st.success(message)
                st.balloons()
                go_to("login")
            else:
                st.error(message)
    with col2:
        if st.button("Back to login", use_container_width=True):
            go_to("login")

# ==================== DASHBOARD PAGE FUNCTIONS ====================
def dashboard_page(go_to, get_user_info, change_password):
    """Display main dashboard with quick shortcuts, portfolio summary, market overview."""
    render_sidebar("Menu", actions=[
        {'label': 'Detailed Stock Analysis', 'callback': lambda: go_to("stock_analysis"), 'key': 'sidebar_stock'},
        {'label': 'Portfolios', 'callback': lambda: go_to("portfolios")}
    ])
    
    st.title("Dashboard")
    st.markdown(f"### Welcome back, **{st.session_state.username}**!")
    st.divider()
    
    # Quick action tiles
    st.subheader("Quick Actions")
    user_portfolios = get_user_portfolios(st.session_state.username)
    
    if user_portfolios:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Create New Portfolio", type="primary", use_container_width=True):
                go_to("create_portfolio")
        with col2:
            if st.button("View All Portfolios", use_container_width=True):
                go_to("portfolios")
        with col3:
            if st.button("Search Stocks", use_container_width=True):
                go_to("stock_analysis")
    else:
        # User has no portfolios → show alternative options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create Your First Portfolio", type="primary", use_container_width=True):
                go_to("create_portfolio")
        with col2:
            if st.button("Detailed Stock Analysis", use_container_width=True):
                go_to("stock_analysis")
    
    st.divider()
    st.subheader("Your Portfolios Summary")
    
    # Portfolio summary table
    if user_portfolios:
        total_invested = sum(calculate_portfolio_value(p.get('stocks', [])) for p in user_portfolios)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Portfolios", len(user_portfolios))
        with col2:
            st.metric("Total Stocks", sum(len(p.get('stocks', [])) for p in user_portfolios))
        with col3:
            st.metric("Total Invested", f"${total_invested:,.2f}")
        with col4:
            avg_value = total_invested / len(user_portfolios) if user_portfolios else 0
            st.metric("Avg Portfolio", f"${avg_value:,.2f}")
        
        st.divider()
        st.subheader("Portfolio Overview")

        # Build portfolio overview table
        portfolio_data = []
        for portfolio in user_portfolios:
            stocks = portfolio.get('stocks', [])
            invested = calculate_portfolio_value(stocks)
            _, predicted_value, _ = get_portfolio_predictions(stocks)
            predicted_change_pct = ((predicted_value - invested) / invested * 100) if invested > 0 else 0
            top_holdings = ", ".join([f"{s.get('symbol', 'N/A')} ({s.get('shares', 1)} shares)" for s in stocks[:3]])
            if len(stocks) > 3:
                top_holdings += f" + {len(stocks) - 3} more"
            
            portfolio_data.append({
                "Portfolio Name": portfolio.get('portfolio_name', 'Unnamed'),
                "Total Value": f"${invested:,.2f}",
                "Predicted Value (1Y)": f"${predicted_value:,.2f}",
                "Expected Change": f"{predicted_change_pct:+.1f}%",
                "Stocks": len(stocks),
                "Markets": ", ".join(portfolio.get('countries', [])) or "N/A",
                "Top Holdings": top_holdings or "No stocks"
            })
        
        if portfolio_data:
            st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True, hide_index=True)
    
    else:
        pass

    st.divider()
    st.subheader("Community Portfolios")

    # Community portfolio showcase (top 5 others)
    all_portfolios = get_all_portfolios()
    if all_portfolios:
        other_portfolios = [p for p in all_portfolios if p.get('user_id') != st.session_state.username][:5]
        for portfolio in other_portfolios:
            stocks = portfolio.get('stocks', [])
            total_value = calculate_portfolio_value(stocks)
            _, predicted_value, _ = get_portfolio_predictions(stocks)
            predicted_change_pct = ((predicted_value - total_value) / total_value * 100) if total_value > 0 else 0
            
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 2])
            with col1:
                st.write(f"**{portfolio.get('user_id', 'Unknown User')}**")
            with col2:
                st.metric("Purchase Value", f"${total_value:,.2f}")
            with col3:
                st.metric("Predicted (1Y)", f"${predicted_value:,.2f}", f"{predicted_change_pct:+.1f}%")
            with col4:
                st.metric("Stocks", len(stocks))
            with col5:
                # View button
                if st.button("View", key=f"media_{portfolio['_id']}", use_container_width=True):
                    st.session_state.media_portfolio_id = str(portfolio['_id'])
                    st.session_state.media_portfolio_owner = portfolio.get('user_id', 'Unknown')
                    go_to("media_portfolio_view")
            if stocks:
                # Show top holdings
                holdings = ", ".join([s.get('symbol', 'N/A') for s in stocks[:3]])
                if len(stocks) > 3:
                    holdings += f" +{len(stocks) - 3} more"
                st.write(f"Holdings: {holdings}")
            st.markdown("---")
    
    st.divider()
    st.subheader("Global Stock Market Dashboard")

    # Fetch market snapshots across all countries
    all_countries_data = {}
    for country, symbols in STOCK_SYMBOLS_BY_COUNTRY.items():
        country_data = get_multiple_stocks_data(symbols[:6], 365)
        if country_data:
            all_countries_data[country] = country_data
    
    # Display market charts per country
    if all_countries_data:
        tabs = st.tabs(list(all_countries_data.keys()))
        for tab, (country, country_data) in zip(tabs, all_countries_data.items()):
            with tab:
                st.write(f"### {country} Stock Market")
                cols = st.columns(3)

                # Show 6 stock trends per country
                for idx, (symbol, data) in enumerate(country_data.items()):
                    with cols[idx % 3]:
                        if isinstance(data, pd.DataFrame) and not data.empty:
                            latest = data.iloc[-1]
                            previous = data.iloc[-2] if len(data) > 1 else latest
                            change_pct = ((float(latest["Close"]) - float(previous["Close"])) / float(previous["Close"])) * 100
                            st.markdown(f"**{symbol}**")
                            st.metric("Price", f"${float(latest['Close']):.2f}", delta=f"{change_pct:+.2f}%")
                            if 'Close' in data.columns:
                                st.line_chart(data['Close'].tail(365).round(2), height=150)
                            st.markdown("---")

# ==================== STOCK ANALYSIS PAGE FUNCTIONS ====================
def stock_analysis_page(go_to, get_user_info, change_password):
    """Main stock analysis page where users can search and view detailed stock analytics."""

    # Build a master list of symbols for sidebar search
    all_symbols = sorted(list(set([s for symbols in STOCK_SYMBOLS_BY_COUNTRY.values() for s in symbols])))
    
    # Sidebar: stock search + options
    with st.sidebar:
        st.header("Stock Analysis")

        # Stock symbol search
        st.subheader("Stock Search")
        search_query = st.text_input("Search Symbol", value="AAPL", placeholder="Type to search...")
        
        if search_query:
            # Filter symbols by search term
            filtered = [s for s in all_symbols if search_query.upper() in s.upper()][:10]

            if filtered:
                cols = st.columns(2)
                for idx, stock in enumerate(filtered):
                    with cols[idx % 2]:
                        if st.button(stock, key=f"search_{stock}", use_container_width=True):
                            st.session_state.selected_stock_symbol = stock
                            st.rerun()
        
        # Selected symbol (stored in session)
        selected_stock = st.session_state.get('selected_stock_symbol', search_query.upper() if search_query else "AAPL")
        
        # Analysis options
        st.subheader("Analysis Tools")
        show_volume = st.checkbox("Show Volume", value=True)
        show_moving_avg = st.checkbox("Show Moving Average", value=False)
        st.divider()

        # Back navigation
        if st.button("← Back to Dashboard", use_container_width=True):
            go_to("dashboard")
    
    # Main content header
    st.title(f"{selected_stock} - Detailed Analysis")

    # Fetch 10-year data for analysis
    data = get_stock_data(selected_stock, 3650)
    
    if isinstance(data, pd.DataFrame) and not data.empty:

        # Show top metrics: current price, 52-week range, volume
        display_stock_metrics(data, selected_stock)
        st.divider()

        # Show price & volume charts
        display_stock_chart(data, show_volume, show_moving_avg)
        st.divider()

        # Recent performance (1-day, 7-day, 30-day)
        col1, col2 = st.columns([2, 3])
        with col1:
            st.subheader("Recent Performance")
            perf_data = []
            for period in [1, 7, 30]:
                if len(data) > period:
                    old_price = float(data.iloc[-(period+1)]['Close'])
                    current_price = float(data.iloc[-1]['Close'])
                    change = ((current_price - old_price) / old_price) * 100
                    perf_data.append({'Period': f'{period} Day{"s" if period > 1 else ""}', 'Change (%)': f'{change:+.2f}%'})
            if perf_data:
                st.table(pd.DataFrame(perf_data))
        
        # Summary descriptive statistics
        with col2:
            st.subheader("Price Statistics")
            stats = [
                {'Metric': 'Average', 'Value': f"${data['Close'].mean():.2f}"},
                {'Metric': 'Median', 'Value': f"${data['Close'].median():.2f}"},
                {'Metric': 'Std Deviation', 'Value': f"${data['Close'].std():.2f}"},
                {'Metric': 'Range', 'Value': f"${data['Close'].max() - data['Close'].min():.2f}"}
            ]
            st.table(pd.DataFrame(stats))
        
        st.divider()
        st.subheader("Price Prediction Using Linear Regression")

        # Linear regression forecast (1-year)
        price_data = data['Close'].dropna()
        
        if len(price_data) >= 30:
            prediction = calculate_stock_prediction(price_data, 365)
            if prediction:
                current_price = prediction['current_price']
                predicted_1y = prediction['predicted_price']
                change = predicted_1y - current_price
                change_pct = (change / current_price) * 100
                
                # Show predicted metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Price", f"${current_price:.2f}")
                with col2:
                    st.metric("Predicted (1Y)", f"${predicted_1y:.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")
                with col3:
                    st.metric("R² Score", f"{prediction['r_squared']:.4f}")
                
                 # Visualization of forecast
                st.subheader("Prediction Visualization")
                lookback = min(730, len(price_data))
                recent_data = price_data.tail(lookback)
                future_dates = pd.date_range(start=recent_data.index[-1] + timedelta(days=1), periods=365, freq='D')
                
                # Build combined plot data
                combined_dates = list(recent_data.index) + list(future_dates)
                combined_actual = list(recent_data.values) + [None] * 365
                combined_pred = [None] * lookback + list(prediction['future_predictions'])
                
                st.line_chart(pd.DataFrame({
                    'Historical Price': combined_actual,
                    'Predicted Trend': combined_pred
                }, index=combined_dates), height=400)
        
        st.divider()

        # Company news link generator
        st.subheader("Company News")
        news_info = get_company_news_link(selected_stock)
        if news_info:
            st.write(f"**Company:** {news_info['company_name']}")
            st.link_button(f"View {news_info['company_name']} News", news_info['news_url'], use_container_width=True)

# ==================== PORTFOLIO MANAGEMENT PAGE FUNCTIONS ====================
def portfolios_page(go_to, get_user_info, change_password):
    """Main page listing user's portfolios with summary, actions, and management tools."""

    render_sidebar("Portfolio Manager", actions=[
        {'label': 'Create New Portfolio', 'callback': lambda: go_to("create_portfolio")},
        {'label': 'Portfolio Analytics', 'callback': lambda: go_to("portfolio_analytics")}
    ], back_button={'label': 'Back to Dashboard', 'callback': lambda: go_to("dashboard")})
    
    st.title("Portfolio Management")
    st.header("Summary")
    user_portfolios = get_user_portfolios(st.session_state.username)

    # Build simple portfolio summary objects
    sample_portfolios = []
    for portfolio in user_portfolios:
        total_value = calculate_portfolio_value(portfolio.get('stocks', []))
        sample_portfolios.append({
            "_id": str(portfolio['_id']),
            "name": portfolio['portfolio_name'],
            "created": portfolio['created_at'].strftime('%Y-%m-%d') if portfolio.get('created_at') else "Unknown",
            "value": total_value,
            "stocks": [s['symbol'] for s in portfolio.get('stocks', [])]
        })
    
    # Show summary metrics
    if sample_portfolios:
        total_value = sum(p["value"] for p in sample_portfolios)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Portfolio Value", f"${total_value:,.2f}")
        with col2:
            st.metric("Number of Portfolios", len(sample_portfolios))
        with col3:
            st.metric("Best Performer", sample_portfolios[0]["name"])
        with col4:
            st.metric("Active Portfolios", len([p for p in sample_portfolios if p.get('value', 0) > 0]))
    
    st.divider()
    st.header("My Portfolios")
    
    # List each portfolio with actions
    if sample_portfolios:
        for portfolio in sorted(sample_portfolios, key=lambda p: p['value'], reverse=True):
            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown(f"### {portfolio['name']}")
                st.write(f"**Created:** {portfolio['created']}")
                st.write(f"**Holdings:** {', '.join(portfolio['stocks']) if portfolio['stocks'] else 'No stocks'}")
            with col2:
                st.metric("Current Value", f"${portfolio['value']:.2f}")
            
            # Action buttons
            col_view, col_edit, col_delete = st.columns(3)
            with col_view:
                if st.button("View", key=f"view_{portfolio['name']}"):
                    st.session_state.view_portfolio_id = portfolio['_id']
                    go_to("portfolio_details")
            with col_edit:
                if st.button("Edit", key=f"edit_{portfolio['name']}"):
                    st.session_state.edit_portfolio_id = portfolio['_id']
                    go_to("edit_portfolio")
            with col_delete:
                if st.button("Delete", key=f"delete_{portfolio['name']}", type="secondary"):
                    st.session_state.confirm_delete_portfolio = portfolio['_id']
                    st.session_state.confirm_delete_name = portfolio['name']
                    st.rerun()
            st.markdown("---")
    
    # Show delete confirmation if user triggered it
    if st.session_state.get('confirm_delete_portfolio'):
        show_delete_confirmation_popup()

# ==================== CREATE PORTFOLIO PAGE FUNCTIONS ====================
def create_portfolio_page(go_to, get_user_info, change_password):
    """Page where users create a new portfolio with selected countries."""

    render_sidebar("Create New Portfolio", back_button={'label': 'Back to Portfolios', 'callback': lambda: go_to("portfolios")})
    
    st.title("Create New Portfolio")
    st.markdown("### Let's build your investment portfolio")
    st.divider()
    
    # Portfolio creation form
    with st.form("create_portfolio_form"):
        st.subheader("Which countries would you like to invest in?")
        selected_countries = st.multiselect("Select countries", AVAILABLE_COUNTRIES, default=["United States"])
        st.divider()
        st.subheader("Portfolio Details")
        portfolio_name = st.text_input("Portfolio Name", placeholder="e.g., My Global Growth Portfolio")
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Create Portfolio", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
    
    if submitted:
        # Required fields: name + at least one country
        if portfolio_name and selected_countries:
            success, message = create_portfolio(st.session_state.username, 
                {'name': portfolio_name, 'countries': selected_countries, 'stocks': []})
            if success:
                st.success("Portfolio created successfully!")
                st.balloons()

                # Set newly created portfolio in session state
                user_portfolios = get_user_portfolios(st.session_state.username)
                if user_portfolios:
                    latest = user_portfolios[0]
                    st.session_state.current_portfolio = {
                        '_id': str(latest['_id']),
                        'name': portfolio_name,
                        'countries': selected_countries,
                        'stocks': []
                    }
                go_to("my_stocks")
            else:
                st.error(f"{message}")
        else:
            st.error("Please fill in all fields")
    elif cancelled:
        go_to("portfolios")

# ==================== MY STOCKS PAGE FUNCTIONS (PORTFOLIO DETAILS + REMOVE STOCKS) ====================
def my_stocks_page(go_to, get_user_info, change_password):
    """Show all stocks inside currently active portfolio and allow removal."""

    portfolio = None

    # Load portfolio from session or database
    if 'current_portfolio' in st.session_state:
        portfolio_id = st.session_state.current_portfolio.get('_id')
        if portfolio_id and portfolio_id != 'temp_id':
            portfolio = get_portfolio_by_id(portfolio_id)
        if not portfolio:
            portfolio = st.session_state.current_portfolio
    
    render_sidebar("My Stocks", actions=[
        {'label': 'Add Stock', 'callback': lambda: go_to("stock_search"), 'type': 'primary'},
        {'label': 'Portfolio Analytics', 'callback': lambda: go_to("portfolio_analytics")}
    ], back_button={'label': 'Back to Portfolios', 'callback': lambda: go_to("portfolios")})
    
    st.title("My Portfolio")
    
    # Portfolio metrics
    if portfolio:
        name = portfolio.get('portfolio_name', portfolio.get('name', 'Unknown'))
        st.markdown(f"### Portfolio: **{name}**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Stocks Added", len(portfolio.get('stocks', [])))
        with col2:
            st.metric("Total Value", f"${calculate_portfolio_value(portfolio.get('stocks', [])):.2f}")
    
    st.divider()
    st.subheader("Stock Holdings")
    
    # Show each stock in portfolio
    if portfolio and portfolio.get('stocks'):
        for idx, stock in enumerate(portfolio['stocks']):
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1.5, 1])
            with col1:
                st.write(f"**{stock['symbol']}**")
            with col2:
                st.write(f"${stock.get('price', 0):.2f}")
            with col3:
                st.write(f"{stock.get('shares', 0)}")
            with col4:
                st.write(f"${stock.get('price', 0) * stock.get('shares', 0):.2f}")
            
            # Remove stock button
            with col5:
                if st.button("Remove", key=f"remove_{idx}"):
                    portfolio_id = st.session_state.current_portfolio.get('_id')
                    if portfolio_id and portfolio_id != 'temp_id':
                        success, _ = remove_stock_from_portfolio(portfolio_id, stock['symbol'])
                        if success:
                            st.success(f"Removed {stock['symbol']}")
                            st.rerun()
            st.markdown("---")
    else:
        # No stocks yet
        if st.button("Add Your First Stock", type="primary", use_container_width=True):
            go_to("stock_search")

# ==================== STOCK SEARCH PAGE FUNCTIONS (ADD STOCKS TO PORTFOLIO) ====================
def stock_search_page(go_to, get_user_info, change_password):
    """Search available stocks from all markets and add them to a portfolio."""

    if 'current_portfolio' not in st.session_state:
        st.warning("No portfolio selected.")
        if st.button("Go to Portfolios"):
            go_to("portfolios")
        st.stop()
    
    render_sidebar("Stock Search", back_button={'label': 'Back to My Stocks', 'callback': lambda: go_to("my_stocks")})
    
    st.title("Stock Search")
    st.markdown("### Find and add stocks to your portfolio")
    
    # Search term
    search_query = st.text_input("Search stocks", placeholder="e.g., AAPL, Tesla")

    # Load all stocks from all countries
    all_stocks = []
    for country in STOCK_SYMBOLS_BY_COUNTRY.keys():
        all_stocks.extend(get_stocks_for_search(country))
    
    # Apply search filter
    filtered = [s for s in all_stocks if search_query.upper() in s["symbol"] or search_query.lower() in s["name"].lower()] if search_query else all_stocks
    
    st.divider()

    # Show up to 20 results
    for stock in filtered[:20]:
        col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 1.5, 2])
        with col1:
            st.write(f"**{stock['symbol']}** - {stock['name']}")
        with col2:
            st.write(f"{stock['country']}")
        with col3:
            st.write(f"${stock['price']:.2f}")
        with col4:
            st.write(f"{stock['change']:+.2f}")

        # Stock add form
        with col5:
            with st.form(key=f"add_{stock['symbol']}"):
                shares = st.number_input("Shares", min_value=1, value=1, key=f"shares_{stock['symbol']}")
                purchase_price = st.number_input("Price ($)", min_value=0.01, value=float(stock['price']), 
                                               step=0.01, key=f"price_{stock['symbol']}")
                if st.form_submit_button("Add", use_container_width=True):
                    new_stock = {
                        'symbol': stock['symbol'], 'name': stock['name'],
                        'purchase_price': purchase_price, 'current_price': stock['price'],
                        'price': purchase_price, 'shares': shares
                    }
                    portfolio_id = st.session_state.current_portfolio.get('_id')
                    if portfolio_id and portfolio_id != 'temp_id':
                        success, msg = add_stock_to_portfolio(portfolio_id, new_stock)
                        if success:
                            st.success(f"Added {shares} shares of {stock['symbol']}!")
                            st.rerun()
                        else:
                            st.error(f"Failed: {msg}")
        st.markdown("---")

# ==================== EDIT PORTFOLIO PAGE FUNCTIONS ====================
def edit_portfolio_page(go_to, get_user_info, change_password):
    """Page allowing user to rename portfolio and modify stock quantities."""

    # Must have portfolio loaded
    if 'edit_portfolio_id' not in st.session_state:
        st.error("No portfolio selected")
        go_to("portfolios")
        return
    
    portfolio = get_portfolio_by_id(st.session_state.edit_portfolio_id)
    if not portfolio:
        st.error("Portfolio not found")
        go_to("portfolios")
        return
    
    render_sidebar("Edit Portfolio", back_button={'label': 'Back to Portfolios', 'callback': lambda: go_to("portfolios")})
    
    st.title("Edit Portfolio")
    st.subheader("Portfolio Information")
    
    # Portfolio name edit field
    col1, col2 = st.columns([3, 1])
    with col1:
        # Save name
        if st.session_state.get('editing_portfolio_name'):
            new_name = st.text_input("Portfolio Name", value=portfolio['portfolio_name'])
        else:
            st.markdown(f"**Current Name:** {portfolio['portfolio_name']}")
    with col2:
        if st.session_state.get('editing_portfolio_name'):
            if st.button("Save"):
                success, _ = update_portfolio(st.session_state.edit_portfolio_id, {'portfolio_name': new_name.strip()})
                if success:
                    st.success("Name updated!")
                    st.session_state.editing_portfolio_name = False
                    st.rerun()
        else:
            # Switch to edit mode
            if st.button("Edit Name"):
                st.session_state.editing_portfolio_name = True
                st.rerun()
    
    st.divider()
    st.subheader("Manage Stocks")
    

    if portfolio.get('stocks'):
        for idx, stock in enumerate(portfolio['stocks']):
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1, 1.5, 1])
            with col1:
                st.write(f"**{stock['symbol']}**")
            with col2:
                st.write(f"${stock.get('price', 0):.2f}")
            
            # Editable share count
            with col3:
                new_shares = st.number_input("Shares", min_value=0, value=stock.get('shares', 1), key=f"sh_{idx}")
            with col4:
                st.write(f"${stock.get('price', 0) * new_shares:.2f}")
            
            # Remove stock
            with col5:
                if st.button("Remove", key=f"rm_{idx}"):
                    remove_stock_from_portfolio(st.session_state.edit_portfolio_id, stock['symbol'])
                    st.rerun()
            st.markdown("---")

# ==================== PORTFOLIO DETAILS PAGE FUNCTIONS ====================
def portfolio_details_page(go_to, get_user_info, change_password):
    """Page showing full portfolio summary and predictions."""

    if 'view_portfolio_id' not in st.session_state:
        st.error("No portfolio selected")
        go_to("portfolios")
        return
    
    portfolio = get_portfolio_by_id(st.session_state.view_portfolio_id)
    if not portfolio:
        st.error("Portfolio not found")
        go_to("portfolios")
        return
    
    # Sidebar with actions (edit, analytics)
    render_sidebar("Portfolio Details", actions=[
        {'label': 'Edit Portfolio', 'callback': lambda: (setattr(st.session_state, 'edit_portfolio_id', st.session_state.view_portfolio_id), go_to("edit_portfolio")), 'type': 'primary'},
        {'label': 'Portfolio Analytics', 'callback': lambda: (setattr(st.session_state, 'analytics_portfolio_id', st.session_state.view_portfolio_id), go_to("portfolio_analytics"))}
    ], back_button={'label': 'Back to Portfolios', 'callback': lambda: go_to("portfolios")})
    
    st.title("Portfolio Details")
    st.markdown(f"### {portfolio['portfolio_name']}")
    
    stocks = portfolio.get('stocks', [])
    if not stocks:
        st.info("No stocks in this portfolio yet")
        return
    
    # Simplified gain/loss (purchase only)
    total_purchase = calculate_portfolio_value(stocks)
    total_current = total_purchase  # Simplified - would normally fetch current prices
    total_gain = total_current - total_purchase
    gain_pct = (total_gain / total_purchase * 100) if total_purchase > 0 else 0
    
    # Show portfolio value metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Purchase Value", f"${total_purchase:.2f}")
    with col2:
        st.metric("Current Value", f"${total_current:.2f}")
    with col3:
        st.markdown("**Total Gain/Loss**")
        st.markdown(f"${total_gain:+.2f}")
        st.markdown(format_percentage_with_color(gain_pct), unsafe_allow_html=True)
    
    st.divider()
    st.subheader("Stock Holdings Detail")
    
    # Show each stock
    for stock in stocks:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"**{stock['symbol']}** - {stock.get('name', stock['symbol'])}")
        with col2:
            st.write(f"Shares: {stock.get('shares', 1)}")
        with col3:
            value = stock.get('price', 0) * stock.get('shares', 1)
            st.write(f"Value: ${value:.2f}")
        st.markdown("---")
    
    st.divider()

    # Show long-term prediction model for entire portfolio
    display_portfolio_predictions(stocks)

# ==================== PORTFOLIO ANALYTICS PAGE FUNCTIONS ====================
def portfolio_analytics_page(go_to, get_user_info, change_password):
    """High-level analytics for a single portfolio or user's combined portfolio."""

    render_sidebar("Portfolio Analytics", back_button={'label': 'Back to Portfolios', 'callback': lambda: go_to("portfolios")})
    
    st.title("Portfolio Analytics & Predictions")
    
    # Show one portfolio (selected)
    if 'analytics_portfolio_id' in st.session_state:
        portfolio = get_portfolio_by_id(st.session_state.analytics_portfolio_id)
        if not portfolio:
            st.error("Portfolio not found")
            return
        st.markdown(f"### Analyzing: {portfolio['portfolio_name']}")
        stocks = portfolio.get('stocks', [])
    
    # Or combine all stocks across user portfolios
    else:
        st.markdown("### Analyzing: All Portfolios")
        user_portfolios = get_user_portfolios(st.session_state.username)
        stocks = [s for p in user_portfolios for s in p.get('stocks', [])]
    
    if not stocks:
        st.info("No stocks to analyze")
        return
    
    # Show predictions chart and summary
    display_portfolio_predictions(stocks)

# ==================== MEDIA PORTFOLIO VIEW PAGE FUNCTIONS ====================
def media_portfolio_view_page(go_to, get_user_info, change_password):
    """Public read-only page showing another user's portfolio."""

    if 'media_portfolio_id' not in st.session_state:
        st.error("No portfolio selected")
        go_to("dashboard")
        return
    
    portfolio = get_portfolio_by_id(st.session_state.media_portfolio_id)
    if not portfolio:
        st.error("Portfolio not found")
        go_to("dashboard")
        return
    
    owner = st.session_state.get('media_portfolio_owner', portfolio.get('user_id', 'Unknown'))
    
    render_sidebar("Community Portfolio", back_button={'label': 'Back to Dashboard', 'callback': lambda: go_to("dashboard")})
    
    st.title(f"{owner}'s Portfolio")
    
    stocks = portfolio.get('stocks', [])
    if not stocks:
        st.info("This portfolio has no stocks")
        return
    
    # Show total value
    total_value = calculate_portfolio_value(stocks)
    st.metric("Portfolio Value", f"${total_value:.2f}")
    
    st.divider()
    st.subheader("Holdings")

    # Show each stock
    for stock in stocks:
        st.write(f"**{stock['symbol']}** - {stock.get('shares', 1)} shares @ ${stock.get('price', 0):.2f}")
        st.markdown("---")
    
    st.divider()

    # Show predicted 1-year trend for full portfolio
    display_portfolio_predictions(stocks)