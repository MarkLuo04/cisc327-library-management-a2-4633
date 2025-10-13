import pytest
from library_service import borrow_book_by_patron, add_book_to_catalog

def test_borrow_book_valid_input():
    """Test borrowing a book with valid patron ID and book ID."""
    add_book_to_catalog("Test Book", "Test Author", "1234567890123", 3)
    
    success, message = borrow_book_by_patron("123456", 1)
    
    assert success == True
    assert "successfully borrowed" in message.lower()
    assert "due date" in message.lower()

def test_borrow_book_patron_id_6_digits():
    """Test that patron ID must be 6-digit format."""
    success, message = borrow_book_by_patron("12345", 1)
    
    assert success == False
    assert "invalid patron id" in message.lower()
    assert "6 digits" in message.lower()

def test_borrow_book_availability_check():
    """Test that book availability is checked."""
    # Add a book with 1 copy
    add_book_to_catalog("Limited Book", "Test Author", "1111111111111", 1)
    
    # Borrow the only copy
    borrow_book_by_patron("123456", 1)
    
    # Try to borrow the same book again
    success, message = borrow_book_by_patron("789012", 1)
    
    assert success == False
    assert "not available" in message.lower()

def test_borrow_book_max_5_books():
    """Test that patron borrowing limit is max 5 books."""
    # Add multiple books to the catalog
    for i in range(7):
        add_book_to_catalog(f"Book {i}", f"Author {i}", f"123456789012{i}", 1)
    
    patron_id = "123456"
    
    # Borrow 5 books (should all succeed)
    for i in range(1, 6):
        success, message = borrow_book_by_patron(patron_id, i)
        assert success == True, f"Should be able to borrow book {i}"
    
    # Try to borrow the 6th book - this should fail but doesn't due to bug
    success, message = borrow_book_by_patron(patron_id, 6)
    
    # This test will FAIL, proving the bug exists
    # The bug is: if current_borrowed > 5 instead of >= 5
    assert success == False, "BUG DETECTED: Should not allow 6th book, but current logic allows it"
    assert "maximum borrowing limit" in message.lower()

def test_borrow_book_creates_record():
    """Test that borrowing creates borrowing record and updates available copies."""
    # Add a book with 2 copies
    add_book_to_catalog("Test Book", "Test Author", "1234567890123", 2)
    
    # Borrow the book
    success, message = borrow_book_by_patron("123456", 1)
    
    assert success == True
    assert "successfully borrowed" in message.lower()
