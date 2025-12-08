"""
Tests for login.py - Testing actual functions with correct mocking
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from login import (
    verify_user, user_exists, validate_email, register_user,
    update_last_login, get_user_info, change_password,
    create_portfolio, get_user_portfolios, get_portfolio_by_id,
    update_portfolio, delete_portfolio, add_stock_to_portfolio,
    remove_stock_from_portfolio, get_collection_safely
)


class TestEmailValidation(unittest.TestCase):
    """Test email validation function"""

    def test_validate_email_valid(self):
        """Test email validation with valid emails"""
        valid_emails = [
            "test@example.com",
            "user.name@example.co.uk",
            "user+tag@example.com"
        ]
        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(validate_email(email))

    def test_validate_email_invalid(self):
        """Test email validation with invalid emails"""
        invalid_emails = [
            "invalid",
            "@example.com",
            "user@",
            "user@.com"
        ]
        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertFalse(validate_email(email))


class TestUserVerification(unittest.TestCase):
    """Test user verification function"""

    @patch('login.get_users_collection')
    def test_verify_user_correct_password(self, mock_get_collection):
        """Test user verification with correct password"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "username": "testuser",
            "password": "testpass123"  # Plain text
        }
        mock_get_collection.return_value = mock_collection

        result = verify_user("testuser", "testpass123")
        self.assertTrue(result)

    @patch('login.get_users_collection')
    def test_verify_user_wrong_password(self, mock_get_collection):
        """Test user verification with wrong password"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "username": "testuser",
            "password": "testpass123"
        }
        mock_get_collection.return_value = mock_collection

        result = verify_user("testuser", "wrongpass")
        self.assertFalse(result)

    @patch('login.get_users_collection')
    def test_verify_user_not_found(self, mock_get_collection):
        """Test user verification when user doesn't exist"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_get_collection.return_value = mock_collection

        result = verify_user("nonexistent", "password")
        self.assertFalse(result)


class TestUserExists(unittest.TestCase):
    """Test user existence checking"""

    @patch('login.get_users_collection')
    def test_user_exists_true(self, mock_get_collection):
        """Test when user exists"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {"username": "testuser"}
        mock_get_collection.return_value = mock_collection

        result = user_exists("testuser")
        self.assertTrue(result)

    @patch('login.get_users_collection')
    def test_user_exists_false(self, mock_get_collection):
        """Test when user doesn't exist"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_get_collection.return_value = mock_collection

        result = user_exists("nonexistent")
        self.assertFalse(result)


class TestUserRegistration(unittest.TestCase):
    """Test user registration function - returns (bool, message) tuple"""

    @patch('login.get_users_collection')
    @patch('login.user_exists')
    def test_register_user_success(self, mock_user_exists, mock_get_collection):
        """Test successful user registration"""
        mock_user_exists.return_value = False
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None  # Email doesn't exist
        mock_collection.insert_one.return_value = MagicMock(inserted_id="user123")
        mock_get_collection.return_value = mock_collection

        success, message = register_user("newuser", "password123", "new@example.com")
        
        self.assertTrue(success)
        self.assertEqual(message, "Registration successful")
        mock_collection.insert_one.assert_called_once()

    @patch('login.get_users_collection')
    @patch('login.user_exists')
    def test_register_user_already_exists(self, mock_user_exists, mock_get_collection):
        """Test registration when user already exists"""
        # Mock get_users_collection to return a valid collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        
        # Mock user_exists to return True
        mock_user_exists.return_value = True

        success, message = register_user("existinguser", "password123", "existing@example.com")
        
        self.assertFalse(success)
        self.assertEqual(message, "Username already exists")

    @patch('login.get_users_collection')
    @patch('login.user_exists')
    def test_register_user_invalid_email(self, mock_user_exists, mock_get_collection):
        """Test registration with invalid email"""
        # Mock get_users_collection to return a valid collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        
        # Mock user_exists to return False so we get to email validation
        mock_user_exists.return_value = False

        success, message = register_user("newuser", "password123", "invalid-email")
        
        self.assertFalse(success)
        self.assertEqual(message, "Please enter a valid email address")

    @patch('login.get_users_collection')
    def test_register_user_empty_username(self, mock_get_collection):
        """Test registration with empty username"""
        # Mock get_users_collection to return a valid collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        success, message = register_user("", "password123", "new@example.com")
        
        self.assertFalse(success)
        self.assertEqual(message, "All fields are required")

    @patch('login.get_users_collection')
    def test_register_user_empty_password(self, mock_get_collection):
        """Test registration with empty password"""
        # Mock get_users_collection to return a valid collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        success, message = register_user("newuser", "", "new@example.com")
        
        self.assertFalse(success)
        self.assertEqual(message, "All fields are required")

    @patch('login.get_users_collection')
    def test_register_user_short_username(self, mock_get_collection):
        """Test registration with short username"""
        # Mock get_users_collection to return a valid collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        success, message = register_user("ab", "password123", "new@example.com")
        
        self.assertFalse(success)
        self.assertEqual(message, "Username must be at least 3 characters long")


class TestPasswordChange(unittest.TestCase):
    """Test password change function - returns (bool, message) tuple"""

    @patch('login.get_users_collection')
    @patch('login.verify_user')
    def test_change_password_success(self, mock_verify, mock_get_collection):
        """Test successful password change"""
        mock_verify.return_value = True
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_get_collection.return_value = mock_collection

        success, message = change_password("testuser", "oldpass", "newpass123")
        
        self.assertTrue(success)
        self.assertEqual(message, "Password changed successfully")

    @patch('login.verify_user')
    def test_change_password_wrong_old_password(self, mock_verify):
        """Test password change with wrong old password"""
        mock_verify.return_value = False

        success, message = change_password("testuser", "wrongpass", "newpass123")
        
        self.assertFalse(success)
        self.assertEqual(message, "Current password is incorrect")


class TestGetUserInfo(unittest.TestCase):
    """Test get user info function"""

    @patch('login.get_users_collection')
    def test_get_user_info_success(self, mock_get_collection):
        """Test getting user info"""
        mock_collection = MagicMock()
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
            "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc)
        }
        mock_collection.find_one.return_value = user_data
        mock_get_collection.return_value = mock_collection

        result = get_user_info("testuser")
        
        self.assertEqual(result["username"], "testuser")
        self.assertEqual(result["email"], "test@example.com")


class TestPortfolioOperations(unittest.TestCase):
    """Test portfolio CRUD operations"""

    @patch('login.get_portfolios_collection')
    def test_create_portfolio_success(self, mock_get_collection):
        """Test successful portfolio creation - returns (bool, message) tuple"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None  # Portfolio name doesn't exist
        mock_collection.insert_one.return_value = MagicMock(inserted_id="portfolio123")
        mock_get_collection.return_value = mock_collection

        portfolio_data = {
            "name": "Test Portfolio",
            "countries": ["United States"],
            "stocks": []
        }
        
        success, message = create_portfolio("testuser", portfolio_data)
        
        self.assertTrue(success)
        self.assertEqual(message, "Portfolio created successfully")
        mock_collection.insert_one.assert_called_once()

    @patch('login.get_portfolios_collection')
    def test_get_user_portfolios(self, mock_get_collection):
        """Test getting user portfolios"""
        mock_collection = MagicMock()
        portfolios = [
            {"_id": "1", "user_id": "testuser", "portfolio_name": "Portfolio 1"},
            {"_id": "2", "user_id": "testuser", "portfolio_name": "Portfolio 2"}
        ]
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = portfolios
        mock_collection.find.return_value = mock_cursor
        mock_get_collection.return_value = mock_collection

        result = get_user_portfolios("testuser")
        
        self.assertEqual(len(result), 2)

    @patch('login.ObjectId')
    @patch('login.get_portfolios_collection')
    def test_get_portfolio_by_id(self, mock_get_collection, mock_object_id):
        """Test getting portfolio by ID"""
        mock_collection = MagicMock()
        portfolio_data = {
            "_id": "portfolio123",
            "portfolio_name": "Test Portfolio"
        }
        mock_collection.find_one.return_value = portfolio_data
        mock_get_collection.return_value = mock_collection
        
        # Mock ObjectId to return the string as-is
        mock_object_id.return_value = "portfolio123"

        result = get_portfolio_by_id("portfolio123")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["portfolio_name"], "Test Portfolio")

    @patch('login.get_portfolios_collection')
    def test_update_portfolio(self, mock_get_collection):
        """Test portfolio update"""
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_get_collection.return_value = mock_collection

        update_data = {"portfolio_name": "Updated Portfolio"}
        
        result = update_portfolio("portfolio123", update_data)
        
        self.assertTrue(result)

    @patch('login.get_portfolios_collection')
    def test_delete_portfolio(self, mock_get_collection):
        """Test portfolio deletion"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {"user_id": "testuser"}
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_get_collection.return_value = mock_collection

        result = delete_portfolio("portfolio123", "testuser")
        
        self.assertTrue(result)


class TestStockOperations(unittest.TestCase):
    """Test stock operations within portfolios"""

    @patch('login.get_portfolios_collection')
    def test_add_stock_to_portfolio(self, mock_get_collection):
        """Test adding stock to portfolio"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "_id": "portfolio123",
            "stocks": []
        }
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_get_collection.return_value = mock_collection

        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "purchase_price": 150.00,
            "shares": 10
        }
        
        result = add_stock_to_portfolio("portfolio123", stock_data)
        
        self.assertTrue(result)

    @patch('login.get_portfolios_collection')
    def test_remove_stock_from_portfolio(self, mock_get_collection):
        """Test removing stock from portfolio"""
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {
            "_id": "portfolio123",
            "stocks": [
                {"symbol": "AAPL", "name": "Apple Inc."}
            ]
        }
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_get_collection.return_value = mock_collection

        result = remove_stock_from_portfolio("portfolio123", "AAPL")
        
        self.assertTrue(result)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""

    @patch('login.get_users_collection')
    def test_update_last_login(self, mock_get_collection):
        """Test updating last login timestamp - returns None"""
        mock_collection = MagicMock()
        mock_collection.update_one.return_value = MagicMock(modified_count=1)
        mock_get_collection.return_value = mock_collection

        result = update_last_login("testuser")
        
        # update_last_login returns None, so we just check it doesn't raise
        self.assertIsNone(result)
        mock_collection.update_one.assert_called_once()

    def test_get_collection_safely_success(self):
        """Test safe collection getter with success"""
        mock_getter = MagicMock(return_value=MagicMock())
        
        collection, error = get_collection_safely(mock_getter)
        
        self.assertIsNotNone(collection)
        self.assertIsNone(error)

    def test_get_collection_safely_failure(self):
        """Test safe collection getter with failure"""
        mock_getter = MagicMock(return_value=None)
        
        collection, error = get_collection_safely(mock_getter)
        
        self.assertIsNone(collection)
        self.assertIsNotNone(error)


if __name__ == '__main__':
    unittest.main()