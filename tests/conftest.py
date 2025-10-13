"""
Pytest configuration file for test fixtures and setup/teardown.
This file runs automatically when pytest is executed.
"""

import pytest
import os
import sqlite3


@pytest.fixture(autouse=True)
def reset_database():
    """
    Automatically reset the database before each test.
    This fixture runs before and after every test function.
    """
    # Setup: Clean database before test
    db_path = 'library.db'
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Initialize fresh database
    from database import init_database
    init_database()
    
    # Run the test
    yield
    
    # Teardown: Clean up after test (optional)
    # The database will be reset again before the next test anyway
