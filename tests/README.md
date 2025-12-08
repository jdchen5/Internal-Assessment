# Test Suite for Stock Portfolio Management Application

This directory contains comprehensive test cases for the portfolio management application.

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── test_database.py           # Database module tests
├── test_login.py              # Authentication logic tests
├── test_ui.py                 # User interface tests (refactored)
├── test_main.py               # Main application tests (refactored)
└── README.md                  # This file
```

## Test Coverage

### 1. Database Module (`test_database.py`)
- **DatabaseConfig class tests:**
  - Connection string management
  - Database connection/disconnection
  - Health checks
  - Index creation
  - Error handling

- **Global functions tests:**
  - Database instance retrieval
  - Collection access (users, portfolios, dashboard_data)
  - Database initialization

### 2. Login Module (`test_login.py`)
- **User management:**
  - User registration with validation
  - User authentication
  - Password change functionality
  - Email validation

- **Portfolio management:**
  - Portfolio creation and deletion
  - Stock addition and removal
  - Portfolio retrieval and updates
  - User portfolio queries

### 3. UI Module (`test_ui.py`) - REFACTORED
- **Utility functions:**
  - Logout handling
  - Percentage formatting with colors
  - Portfolio value calculation
  - Company news link generation

- **Data fetching:**
  - Stock data retrieval from yfinance
  - Historical stock data fetching
  - Stock search functionality
  - Multi-stock data fetching

- **Prediction & Analytics:**
  - Linear regression predictions
  - Portfolio-level predictions
  - Stock price forecasting

- **UI Components:**
  - Sidebar rendering
  - Stock metrics display
  - Stock charts (price and volume)
  - Delete confirmation dialogs

- **Page functions:**
  - Login page behavior
  - Registration page functionality
  - Dashboard with portfolio overview
  - Stock analysis page
  - Portfolio management pages
  - Stock search and addition

### 4. Main Module (`test_main.py`) - REFACTORED
- **Application routing:**
  - All page navigation (12+ routes)
  - Session state management
  - Database initialization handling

- **New routes tested:**
  - stock_analysis
  - portfolios
  - create_portfolio
  - my_stocks
  - stock_search
  - edit_portfolio
  - portfolio_details
  - portfolio_analytics
  - media_portfolio_view

- **Configuration:**
  - Streamlit page setup (wide layout)
  - CSS styling application
  - Connection status indicators

## Running Tests

### Prerequisites
Install test dependencies:
```bash
pip install pytest pytest-mock pandas numpy yfinance
```

### Run All Tests
```bash
pytest
```

### Run Specific Test Files
```bash
pytest tests/test_database.py
pytest tests/test_login.py
pytest tests/test_ui.py
pytest tests/test_main.py
```

### Run Tests with Coverage
```bash
pip install pytest-cov
pytest --cov=src --cov-report=html
```

### Run Tests by Markers
```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run only integration tests
pytest -m database      # Run only database tests
pytest -m ui            # Run only UI tests
pytest -m api           # Run only API-related tests
pytest -m slow          # Run only slow tests
```

### Run Specific Test Classes
```bash
pytest tests/test_ui.py::TestUtilityFunctions
pytest tests/test_ui.py::TestDataFetching
pytest tests/test_ui.py::TestPredictionAnalytics
pytest tests/test_main.py::TestRoutingLogic
```

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Use mocks to isolate dependencies
- Fast execution
- Most of the tests in this suite are unit tests

### Integration Tests
- Test interactions between components
- May require database connections
- Slower execution
- Marked with `@pytest.mark.integration`

### Mock Usage
The tests extensively use mocking to:
- Isolate units under test
- Simulate database responses
- Mock Streamlit components
- Mock yfinance API calls
- Control external dependencies

## Test Fixtures

### Available Fixtures (in `conftest.py`)

#### Core Fixtures
- `mock_streamlit`: Mocks all Streamlit components including new features (st.cache_data, st.dialog, etc.)
- `mock_database_manager`: Mocks database manager and collections
- `mock_pymongo`: Mocks PyMongo client and database operations
- `mock_environment_variables`: Sets up test environment variables

#### Data Fixtures
- `sample_user_data`: Provides sample user data for testing
- `sample_portfolio_data`: Provides sample portfolio with stocks
- `sample_stock_data`: Provides sample pandas DataFrame with stock prices

#### External API Fixtures
- `mock_yfinance`: Mocks yfinance library for stock data fetching
- `mock_constants`: Mocks the constants module with stock symbols

## Common Test Patterns

### Testing Database Operations
```python
@patch('login.get_users_collection')
def test_user_function(self, mock_get_collection):
    mock_collection = MagicMock()
    mock_get_collection.return_value = mock_collection
    
    # Test your function
    result = your_function()
    
    # Assert expectations
    mock_collection.find_one.assert_called_once()
```

### Testing Streamlit UI
```python
@patch('streamlit.button')
@patch('streamlit.text_input')
def test_ui_component(self, mock_text_input, mock_button):
    mock_text_input.side_effect = ["username", "password"]
    mock_button.return_value = True
    
    # Test your UI function
    ui_function()
    
    # Assert UI interactions
    mock_button.assert_called()
```

### Testing Stock Data Fetching
```python
@patch('yfinance.download')
def test_stock_fetch(self, mock_download):
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=30)
    mock_download.return_value = pd.DataFrame({
        'Close': [100, 105, 110]
    }, index=dates)
    
    result = get_stock_data('AAPL', 30)
    
    self.assertIsInstance(result, pd.DataFrame)
```

## Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Mocking**: Use mocks to isolate the code under test from external dependencies
3. **Clear Names**: Test names should clearly describe what is being tested
4. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
5. **Edge Cases**: Test both happy path and error conditions
6. **Data Fixtures**: Use fixtures for consistent test data
7. **Cache Handling**: Mock st.cache_data decorator to avoid caching during tests

## New Features Tested

### Portfolio Features
- Multi-country portfolio creation
- Stock purchase with shares and price tracking
- Portfolio value calculations
- Portfolio predictions using linear regression

### Stock Analysis
- Real-time stock data fetching
- Historical data analysis
- Price predictions (1-year forecast)
- Stock metrics display (52-week high/low, volume)
- Moving averages

### Community Features
- View other users' portfolios
- Global stock market dashboard
- Multi-country stock support

## Troubleshooting

### Common Issues

1. **Import Errors**: 
   - Ensure the `src` directory is in the Python path
   - Check that constants.py is available or mocked

2. **Mock Issues**: 
   - Ensure mocks are patched at the correct location
   - Remember that ui.py imports need to be mocked with full path

3. **Pandas/NumPy Errors**:
   - Ensure pandas and numpy are installed
   - Check that DataFrame operations are properly mocked

4. **Streamlit Warnings**: 
   - Some Streamlit warnings are normal and filtered out
   - st.cache_data should be mocked in conftest.py

5. **yfinance Timeouts**:
   - All yfinance calls should be mocked in tests
   - Use mock_yfinance fixture for consistent behavior

### Running Individual Tests
```bash
# Run a specific test class
pytest tests/test_ui.py::TestUtilityFunctions

# Run a specific test method
pytest tests/test_ui.py::TestUtilityFunctions::test_handle_logout

# Run with verbose output
pytest -v tests/test_ui.py
```

### Debugging Tests
```bash
# Show print statements and verbose output
pytest -s -vv tests/test_ui.py

# Stop on first failure
pytest -x tests/

# Show locals in tracebacks
pytest -l tests/test_main.py
```

## Coverage Goals

Target coverage by module:
- **database.py**: >90% (well-tested core functionality)
- **login.py**: >85% (authentication and portfolio management)
- **ui.py**: >70% (UI components with many external dependencies)
- **main.py**: >80% (routing logic)

Run coverage report:
```bash
pytest --cov=src --cov-report=term-missing
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=src --cov-report=xml
```

## Contributing

When adding new tests:
1. Follow the existing naming conventions
2. Add appropriate docstrings
3. Use the existing fixtures where possible
4. Add new fixtures to conftest.py if needed
5. Add new markers if needed
6. Update this README with new test coverage
7. Ensure all mocks are properly cleaned up
8. Test both success and failure paths

## Test Dependencies

Required packages:
```
pytest>=7.0.0
pytest-mock>=3.10.0
pandas>=1.5.0
numpy>=1.23.0
```

Optional for coverage:
```
pytest-cov>=4.0.0
```

## Notes

- The refactored UI includes real-time stock data fetching, so tests mock yfinance extensively
- Portfolio predictions use linear regression, tested with sample data
- Session state management is critical for routing, thoroughly tested
- All external API calls (yfinance, database) are mocked for speed and reliability