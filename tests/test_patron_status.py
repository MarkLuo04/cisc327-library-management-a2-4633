import pytest
from library_service import get_patron_status_report, add_book_to_catalog, borrow_book_by_patron

def test_patron_status_not_implemented():
    """Test that patron status report returns proper structure."""
    result = get_patron_status_report("123456")
    
    # Should return a dictionary with required keys
    assert isinstance(result, dict)
    assert 'currently_borrowed' in result
    assert 'total_late_fees' in result
    assert 'books_borrowed_count' in result
    assert 'borrowing_history' in result

def test_patron_status_currently_borrowed_books():
    """Test that patron status shows currently borrowed books with due dates (R7 requirement)."""
    # Setup: Add books and borrow them
    add_book_to_catalog("Book 1", "Author 1", "1234567890123", 2)
    add_book_to_catalog("Book 2", "Author 2", "9876543210987", 2)
    borrow_book_by_patron("123456", 1)
    borrow_book_by_patron("123456", 2)
    
    # When implemented, should return currently borrowed books with due dates
    result = get_patron_status_report("123456")
    
    assert isinstance(result, dict)
    assert 'currently_borrowed' in result
    assert isinstance(result['currently_borrowed'], list)
    
    # Should have 2 borrowed books
    assert len(result['currently_borrowed']) >= 2
    
    # Each borrowed book should have title and due_date
    for book in result['currently_borrowed']:
        assert 'title' in book or 'book_title' in book
        assert 'due_date' in book

def test_patron_status_total_late_fees():
    """Test that patron status shows total late fees owed (R7 requirement)."""
    # Setup: Add and borrow a book
    add_book_to_catalog("Test Book", "Test Author", "1234567890123", 1)
    borrow_book_by_patron("123456", 1)
    
    # When implemented, should return total late fees owed
    result = get_patron_status_report("123456")
    
    assert isinstance(result, dict)
    assert 'total_late_fees' in result or 'late_fees' in result
    
    # Late fees should be a numeric value (float or int)
    fee_key = 'total_late_fees' if 'total_late_fees' in result else 'late_fees'
    assert isinstance(result[fee_key], (float, int))
    assert result[fee_key] >= 0

def test_patron_status_books_borrowed_count():
    """Test that patron status shows number of books currently borrowed (R7 requirement)."""
    # Setup: Add books and borrow them
    add_book_to_catalog("Book 1", "Author 1", "1234567890123", 3)
    add_book_to_catalog("Book 2", "Author 2", "9876543210987", 3)
    add_book_to_catalog("Book 3", "Author 3", "1111111111111", 3)
    
    borrow_book_by_patron("123456", 1)
    borrow_book_by_patron("123456", 2)
    borrow_book_by_patron("123456", 3)
    
    # When implemented, should return count of currently borrowed books
    result = get_patron_status_report("123456")
    
    assert isinstance(result, dict)
    assert 'books_borrowed_count' in result or 'currently_borrowed_count' in result or 'borrowed_count' in result
    
    # Count should be an integer
    count_key = next((k for k in ['books_borrowed_count', 'currently_borrowed_count', 'borrowed_count'] if k in result), None)
    assert count_key is not None
    assert isinstance(result[count_key], int)
    assert result[count_key] == 3

def test_patron_status_borrowing_history():
    """Test that patron status shows borrowing history (R7 requirement)."""
    # Setup: Add books and borrow them
    add_book_to_catalog("Book 1", "Author 1", "1234567890123", 2)
    add_book_to_catalog("Book 2", "Author 2", "9876543210987", 2)
    
    borrow_book_by_patron("123456", 1)
    borrow_book_by_patron("123456", 2)
    
    # When implemented, should return borrowing history
    result = get_patron_status_report("123456")
    
    assert isinstance(result, dict)
    assert 'borrowing_history' in result or 'history' in result
    
    history_key = 'borrowing_history' if 'borrowing_history' in result else 'history'
    assert isinstance(result[history_key], list)
    
    # History should contain records
    assert len(result[history_key]) >= 2
    
    # Each history record should have book info and borrow date
    for record in result[history_key]:
        assert isinstance(record, dict)
        assert 'book_id' in record or 'title' in record
        assert 'borrow_date' in record or 'borrowed_date' in record
