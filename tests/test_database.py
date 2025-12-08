"""
Simplified database tests - focuses on testable functions
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import get_db, get_users_collection, get_dashboard_collection, get_portfolios_collection


class TestDatabaseFunctions(unittest.TestCase):
    """Test database helper functions"""

    @patch('database.db_config')
    def test_get_db(self, mock_db_config):
        """Test get_db function"""
        mock_database = MagicMock()
        mock_db_config.get_database.return_value = mock_database
        
        result = get_db()
        
        self.assertEqual(result, mock_database)

    @patch('database.db_config')
    def test_get_users_collection(self, mock_db_config):
        """Test get_users_collection function"""
        mock_collection = MagicMock()
        mock_db_config.get_collection.return_value = mock_collection
        
        result = get_users_collection()
        
        self.assertEqual(result, mock_collection)
        mock_db_config.get_collection.assert_called_once_with("users")

    @patch('database.db_config')
    def test_get_dashboard_collection(self, mock_db_config):
        """Test get_dashboard_collection function"""
        mock_collection = MagicMock()
        mock_db_config.get_collection.return_value = mock_collection
        
        result = get_dashboard_collection()
        
        self.assertEqual(result, mock_collection)
        mock_db_config.get_collection.assert_called_once_with("dashboard_data")

    @patch('database.db_config')
    def test_get_portfolios_collection(self, mock_db_config):
        """Test get_portfolios_collection function"""
        mock_collection = MagicMock()
        mock_db_config.get_collection.return_value = mock_collection
        
        result = get_portfolios_collection()
        
        self.assertEqual(result, mock_collection)
        mock_db_config.get_collection.assert_called_once_with("portfolios")


if __name__ == '__main__':
    unittest.main()