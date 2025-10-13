import pytest
from library_service import add_book_to_catalog

def test_add_book_valid_input():
    """Test adding a book with valid input."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)
    
    assert success == True
    assert "successfully added" in message.lower()

def test_add_book_title_required():
    """Test that title is required."""
    success, message = add_book_to_catalog("", "Test Author", "1234567890123", 5)
    
    assert success == False
    assert "title is required" in message.lower()

def test_add_book_author_required():
    """Test that author is required."""
    success, message = add_book_to_catalog("Test Book", "", "1234567890123", 5)
    
    assert success == False
    assert "author is required" in message.lower()

def test_add_book_isbn_13_digits():
    """Test that ISBN must be exactly 13 digits."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "123456789", 5)
    
    assert success == False
    assert "isbn must be exactly 13 digits" in message.lower()

def test_add_book_positive_copies():
    """Test that total copies must be positive integer."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", -1)
    
    assert success == False
    assert "total copies must be a positive integer" in message.lower()
