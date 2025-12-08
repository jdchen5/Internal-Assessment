"""
Simplified test configuration file for pytest
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone


# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class MockSessionState:
    """Mock Streamlit session state that supports both dict and attribute access"""
    def __init__(self):
        self._data = {}
    
    def __getattr__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        return self._data.get(key)
    
    def __setattr__(self, key, value):
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value
    
    def __contains__(self, key):
        return key in self._data
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def get(self, key, default=None):
        return self._data.get(key, default)


@pytest.fixture
def mock_session_state():
    """Provide a mock session state for tests"""
    return MockSessionState()


@pytest.fixture
def mock_collection():
    """Mock MongoDB collection with basic operations"""
    collection = MagicMock()
    collection.find_one.return_value = None
    collection.insert_one.return_value = MagicMock(inserted_id="test_id")
    collection.update_one.return_value = MagicMock(modified_count=1)
    collection.delete_one.return_value = MagicMock(deleted_count=1)
    collection.find.return_value = MagicMock(sort=MagicMock(return_value=[]))
    return collection


@pytest.fixture
def sample_user():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "password": "testpass123",  # Plain text as per your implementation
        "email": "test@example.com",
        "role": "user",
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "last_login": datetime(2024, 1, 15, tzinfo=timezone.utc),
        "is_active": True
    }


@pytest.fixture
def sample_portfolio():
    """Sample portfolio data for testing"""
    return {
        "_id": "portfolio_123",
        "user_id": "testuser",
        "portfolio_name": "Test Portfolio",
        "countries": ["United States"],
        "stocks": [
            {"symbol": "AAPL", "name": "Apple Inc.", "purchase_price": 150.00, "shares": 10}
        ],
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "is_active": True
    }


@pytest.fixture
def sample_stock():
    """Sample stock data for testing"""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "purchase_price": 150.00,
        "shares": 10
    }


@pytest.fixture(autouse=True)
def mock_streamlit():
    """Auto-mock streamlit to prevent UI-related errors"""
    with patch('streamlit.error'), \
         patch('streamlit.warning'), \
         patch('streamlit.info'), \
         patch('streamlit.success'), \
         patch('streamlit.rerun'), \
         patch('streamlit.set_page_config'):
        yield


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "skip_ui: Skip UI tests (too complex to mock)")
    config.addinivalue_line("markers", "fast: Fast-running tests")