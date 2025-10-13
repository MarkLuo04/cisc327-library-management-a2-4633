import pytest
from library_service import calculate_late_fee_for_book, add_book_to_catalog, borrow_book_by_patron
from datetime import datetime, timedelta
from unittest.mock import patch

def test_late_fee_not_implemented():
    """Test that late fee calculation returns proper structure."""
    result = calculate_late_fee_for_book("123456", 1)
    
    # Should return a dictionary with fee_amount, days_overdue, and status
    assert result is not None
    assert isinstance(result, dict)
    assert 'fee_amount' in result
    assert 'days_overdue' in result
    assert 'status' in result
    assert result['fee_amount'] == 0.00
    assert result['days_overdue'] == 0

def test_late_fee_books_due_14_days():
    """Test that books are due 14 days after borrowing (R5 requirement)."""
    # When implemented, should calculate based on 14-day due period
    # For a book borrowed today and returned on day 15, should be 1 day overdue
    
    # Add and borrow a book
    add_book_to_catalog("Test Book", "Test Author", "1234567890123", 1)
    borrow_book_by_patron("123456", 1)
    
    # Mock return date to be 15 days after borrow (1 day overdue)
    mock_return_date = datetime.now() + timedelta(days=15)
    
    # We need to mock datetime.now() but keep datetime.fromisoformat() working
    with patch('library_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_return_date
        mock_datetime.fromisoformat = datetime.fromisoformat
        result = calculate_late_fee_for_book("123456", 1)
    
    # Should show 1 day overdue and $0.50 fee
    assert result is not None, "Function should return a dictionary, not None"
    assert result['days_overdue'] == 1
    assert result['fee_amount'] == 0.50

def test_late_fee_50_cents_first_7_days():
    """Test that late fee is $0.50/day for first 7 days overdue (R5 requirement)."""
    # When implemented, should charge $0.50/day for days 1-7 overdue
    
    # Add and borrow a book
    add_book_to_catalog("Test Book", "Test Author", "1234567890123", 1)
    borrow_book_by_patron("123456", 1)
    
    # Mock return date to be 21 days after borrow (7 days overdue)
    mock_return_date = datetime.now() + timedelta(days=21)
    
    # We need to mock datetime.now() but keep datetime.fromisoformat() working
    with patch('library_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_return_date
        mock_datetime.fromisoformat = datetime.fromisoformat
        result = calculate_late_fee_for_book("123456", 1)
    
    # Should show 7 days overdue and $3.50 fee (7 * $0.50)
    assert result is not None, "Function should return a dictionary, not None"
    assert result['days_overdue'] == 7
    assert result['fee_amount'] == 3.50

def test_late_fee_1_dollar_after_7_days():
    """Test that late fee is $1.00/day for each additional day after 7 days (R5 requirement)."""
    # When implemented, should charge $1.00/day for days 8+ overdue
    
    # Add and borrow a book
    add_book_to_catalog("Test Book", "Test Author", "1234567890123", 1)
    borrow_book_by_patron("123456", 1)
    
    # Mock return date to be 25 days after borrow (11 days overdue)
    mock_return_date = datetime.now() + timedelta(days=25)
    
    # We need to mock datetime.now() but keep datetime.fromisoformat() working
    with patch('library_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_return_date
        mock_datetime.fromisoformat = datetime.fromisoformat
        result = calculate_late_fee_for_book("123456", 1)
    
    # Should show 11 days overdue and $7.50 fee (7 * $0.50 + 4 * $1.00)
    assert result is not None, "Function should return a dictionary, not None"
    assert result['days_overdue'] == 11
    assert result['fee_amount'] == 7.50

def test_late_fee_max_15_dollars():
    """Test that maximum late fee is $15.00 per book (R5 requirement)."""
    # When implemented, should cap fee at $15.00
    
    # Add and borrow a book
    add_book_to_catalog("Test Book", "Test Author", "1234567890123", 1)
    borrow_book_by_patron("123456", 1)
    
    # Mock return date to be 50 days after borrow (36 days overdue)
    # This would normally be: 7 * $0.50 + 29 * $1.00 = $32.50
    mock_return_date = datetime.now() + timedelta(days=50)
    
    # We need to mock datetime.now() but keep datetime.fromisoformat() working
    with patch('library_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = mock_return_date
        mock_datetime.fromisoformat = datetime.fromisoformat
        result = calculate_late_fee_for_book("123456", 1)
    
    # Should show 36 days overdue but fee capped at $15.00
    # This will fail until implemented, demonstrating TDD
    assert result is not None, "Function should return a dictionary, not None"
    assert result['days_overdue'] == 36
    assert result['fee_amount'] == 15.00
