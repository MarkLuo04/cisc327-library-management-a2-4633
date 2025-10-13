# test_library_service.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import library_service as ls
import database  # patch runtime imports from here when needed


# Helper to make a mock connection whose execute(...).fetchone()/fetchall() return the provided values
def make_mock_conn(fetchone_result=None, fetchall_result=None):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_result
    mock_cursor.fetchall.return_value = fetchall_result
    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    # ensure .close exists
    mock_conn.close = MagicMock()
    return mock_conn


# ------------------------------
# R1: Add Book to Catalog (4-5 tests)
# ------------------------------


@patch("library_service.insert_book")
@patch("library_service.get_book_by_isbn")
def test_add_book_success(mock_get_by_isbn, mock_insert):
    mock_get_by_isbn.return_value = None
    mock_insert.return_value = True

    success, msg = ls.add_book_to_catalog(
        "A Good Title", "Jane Author", "1234567890123", 2
    )
    assert success is True
    assert "successfully added" in msg
    mock_insert.assert_called_once()


def test_add_book_missing_title():
    success, msg = ls.add_book_to_catalog("", "Author", "1234567890123", 1)
    assert success is False
    assert "Title is required" in msg


def test_add_book_title_too_long():
    long_title = "T" * 201
    success, msg = ls.add_book_to_catalog(long_title, "Author", "1234567890123", 1)
    assert success is False
    assert "less than 200 characters" in msg


def test_add_book_invalid_isbn_length():
    success, msg = ls.add_book_to_catalog("Title", "Author", "12345", 1)
    assert success is False
    assert "ISBN must be exactly 13 digits" in msg


@patch("library_service.get_book_by_isbn")
def test_add_book_duplicate_isbn(mock_get_by_isbn):
    mock_get_by_isbn.return_value = {"isbn": "1234567890123"}
    success, msg = ls.add_book_to_catalog("Title", "Author", "1234567890123", 1)
    assert success is False
    assert "already exists" in msg


# ------------------------------
# R3: Book Borrowing (4-5 tests)
# ------------------------------


@patch("library_service.update_book_availability")
@patch("library_service.insert_borrow_record")
@patch("library_service.get_patron_borrow_count")
@patch("library_service.get_book_by_id")
def test_borrow_book_success(
    mock_get_book, mock_borrow_count, mock_insert_record, mock_update_avail
):
    mock_get_book.return_value = {"title": "My Book", "available_copies": 3}
    mock_borrow_count.return_value = 1
    mock_insert_record.return_value = True
    mock_update_avail.return_value = True

    success, msg = ls.borrow_book_by_patron("654321", 10)
    assert success is True
    assert "Successfully borrowed" in msg
    assert "Due date" in msg
    mock_insert_record.assert_called_once()
    mock_update_avail.assert_called_once()


def test_borrow_book_invalid_patron_id_non_digit():
    success, msg = ls.borrow_book_by_patron("12A456", 1)
    assert success is False
    assert "Invalid patron ID" in msg


@patch("library_service.get_book_by_id", return_value=None)
def test_borrow_book_book_not_found(mock_get_book):
    success, msg = ls.borrow_book_by_patron("123456", 9999)
    assert success is False
    assert "Book not found" in msg


@patch("library_service.get_book_by_id")
def test_borrow_book_unavailable(mock_get_book):
    mock_get_book.return_value = {"title": "X", "available_copies": 0}
    success, msg = ls.borrow_book_by_patron("123456", 1)
    assert success is False
    assert "not available" in msg


@patch("library_service.get_book_by_id")
@patch("library_service.get_patron_borrow_count")
def test_borrow_book_limit_reached(mock_borrow_count, mock_get_book):
    mock_get_book.return_value = {"title": "X", "available_copies": 1}
    mock_borrow_count.return_value = 5
    success, msg = ls.borrow_book_by_patron("123456", 1)
    assert success is False
    assert "maximum borrowing limit" in msg


# ------------------------------
# R4: Book Return (4-5 tests)
# ------------------------------


@patch("library_service.update_book_availability", return_value=True)
@patch("library_service.update_borrow_record_return_date", return_value=True)
@patch("library_service.get_book_by_id", return_value={"title": "Returned Book"})
def test_return_book_success(mock_get_book, mock_update_return, mock_update_avail):
    # Use a due date in the future to avoid late fees
    borrow_row = {
        "id": 1,
        "patron_id": "123456",
        "book_id": 2,
        "borrow_date": datetime.now().isoformat(),
        "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
        "return_date": None,
    }
    mock_conn = make_mock_conn(fetchone_result=borrow_row)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        success, msg = ls.return_book_by_patron("123456", 2)
    assert success is True
    assert "Successfully returned" in msg
    # no late fee mention
    assert "Late fee" not in msg


def test_return_book_invalid_patron_id():
    success, msg = ls.return_book_by_patron("12", 1)
    assert success is False
    assert "Invalid patron ID" in msg


@patch("library_service.get_book_by_id", return_value={"title": "Book Exists"})
def test_return_book_no_active_borrow_record(mock_get_book):
    # Simulate no active borrow record found for this patron/book
    mock_conn = make_mock_conn(fetchone_result=None)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        success, msg = ls.return_book_by_patron("123456", 3)
    assert success is False
    assert "No active borrow record" in msg


@patch("library_service.update_borrow_record_return_date", return_value=False)
@patch("library_service.get_book_by_id", return_value={"title": "Book"})
def test_return_book_update_fail(mock_get_book, mock_update_return):
    borrow_row = {"id": 1}
    mock_conn = make_mock_conn(fetchone_result=borrow_row)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        success, msg = ls.return_book_by_patron("123456", 4)
    assert success is False
    assert "Database error occurred while updating return date" in msg


# ------------------------------
# R5: Late Fee Calculation (4-5 tests)
# ------------------------------


def test_late_fee_no_borrow_record():
    mock_conn = make_mock_conn(fetchone_result=None)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        info = ls.calculate_late_fee_for_book("123456", 1)
    assert info["fee_amount"] == 0.00
    assert info["days_overdue"] == 0
    assert info["status"].startswith("No borrow")


def test_late_fee_not_overdue():
    due_date = (datetime.now() + timedelta(days=2)).isoformat()
    row = {"due_date": due_date, "return_date": None}
    mock_conn = make_mock_conn(fetchone_result=row)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        info = ls.calculate_late_fee_for_book("123456", 1)
    assert info["fee_amount"] == 0.00
    assert info["days_overdue"] == 0
    assert info["status"] == "Not overdue"


def test_late_fee_overdue_5_days():
    due_date = (datetime.now() - timedelta(days=5)).isoformat()
    row = {"due_date": due_date, "return_date": None}
    mock_conn = make_mock_conn(fetchone_result=row)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        info = ls.calculate_late_fee_for_book("123456", 1)
    # 5 days * $0.50 = $2.50
    assert info["fee_amount"] == 2.50
    assert info["days_overdue"] == 5
    assert info["status"] == "Overdue"


def test_late_fee_overdue_10_days():
    due_date = (datetime.now() - timedelta(days=10)).isoformat()
    row = {"due_date": due_date, "return_date": None}
    mock_conn = make_mock_conn(fetchone_result=row)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        info = ls.calculate_late_fee_for_book("123456", 1)
    # First 7 days: 7*0.5 = 3.5; remaining 3 days: 3*1 = 3; total = 6.5
    assert info["fee_amount"] == 6.50
    assert info["days_overdue"] == 10


def test_late_fee_capped_at_15():
    due_date = (datetime.now() - timedelta(days=60)).isoformat()
    row = {"due_date": due_date, "return_date": None}
    mock_conn = make_mock_conn(fetchone_result=row)
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        info = ls.calculate_late_fee_for_book("123456", 1)
    assert info["fee_amount"] <= 15.00
    assert info["status"] == "Overdue"


# ------------------------------
# R6: Book Search (4-5 tests)
# ------------------------------


def test_search_books_empty_term_returns_empty():
    results = ls.search_books_in_catalog("", "title")
    assert results == []


def test_search_books_invalid_type_returns_empty():
    # invalid search type should return []
    with patch.object(database, "get_db_connection") as mock_get_conn:
        mock_get_conn.return_value = make_mock_conn()
        results = ls.search_books_in_catalog("something", "publisher")
    assert results == []


def test_search_books_title_partial_match():
    # Simulate DB returning rows
    row = {
        "id": 1,
        "title": "Learning Python",
        "author": "Author",
        "isbn": "1234567890123",
    }
    mock_conn = make_mock_conn(fetchall_result=[row])
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        results = ls.search_books_in_catalog("Python", "title")
    assert isinstance(results, list)
    assert results[0]["title"] == "Learning Python"


def test_search_books_author_partial_match():
    row = {"id": 2, "title": "Book Two", "author": "Jane Doe", "isbn": "9876543210123"}
    mock_conn = make_mock_conn(fetchall_result=[row])
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        results = ls.search_books_in_catalog("doe", "author")
    assert len(results) == 1
    assert results[0]["author"] == "Jane Doe"


def test_search_books_isbn_exact_match():
    row = {"id": 3, "title": "ISBN Book", "author": "X", "isbn": "1111111111111"}
    mock_conn = make_mock_conn(fetchall_result=[row])
    with patch.object(database, "get_db_connection", return_value=mock_conn):
        results = ls.search_books_in_catalog("1111111111111", "isbn")
    assert len(results) == 1
    assert results[0]["isbn"] == "1111111111111"


# ------------------------------
# R7: Patron Status Report (4-5 tests)
# ------------------------------


def test_get_patron_status_invalid_id():
    report = ls.get_patron_status_report("12")
    assert report == {}


def test_get_patron_status_no_current_borrows():
    # get_patron_borrowed_books should return empty list
    with patch.object(
        database, "get_patron_borrowed_books", return_value=[]
    ), patch.object(
        database, "get_db_connection", return_value=make_mock_conn(fetchall_result=[])
    ):
        report = ls.get_patron_status_report("123456")
    assert report["books_borrowed_count"] == 0
    assert report["currently_borrowed"] == []
    assert report["total_late_fees"] == 0.00


def test_get_patron_status_with_current_borrow_and_history():
    # Simulate one currently borrowed book (object shape as expected by function)
    now = datetime.now()
    borrowed_book = {
        "book_id": 7,
        "title": "Current Book",
        "author": "Auth",
        "borrow_date": now,
        "due_date": now + timedelta(days=5),
        "is_overdue": False,
    }
    # Also simulate history rows returned from DB
    history_row = {
        "book_id": 7,
        "title": "Current Book",
        "author": "Auth",
        "borrow_date": now.isoformat(),
        "due_date": (now + timedelta(days=5)).isoformat(),
        "return_date": None,
    }

    with patch.object(
        database, "get_patron_borrowed_books", return_value=[borrowed_book]
    ), patch.object(
        database,
        "get_db_connection",
        return_value=make_mock_conn(fetchall_result=[history_row]),
    ), patch(
        "library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 0.0, "days_overdue": 0},
    ):
        report = ls.get_patron_status_report("123456")

    assert report["books_borrowed_count"] == 1
    assert len(report["borrowing_history"]) == 1
    assert report["total_late_fees"] == 0.00


def test_get_patron_status_with_late_fee_aggregation():
    # one borrowed book with a late fee
    now = datetime.now()
    borrowed_book = {
        "book_id": 8,
        "title": "Late Book",
        "author": "Auth",
        "borrow_date": now,
        "due_date": now - timedelta(days=3),
        "is_overdue": True,
    }
    history_row = {
        "book_id": 8,
        "title": "Late Book",
        "author": "Auth",
        "borrow_date": now.isoformat(),
        "due_date": (now - timedelta(days=3)).isoformat(),
        "return_date": None,
    }

    with patch.object(
        database, "get_patron_borrowed_books", return_value=[borrowed_book]
    ), patch.object(
        database,
        "get_db_connection",
        return_value=make_mock_conn(fetchall_result=[history_row]),
    ), patch(
        "library_service.calculate_late_fee_for_book",
        return_value={"fee_amount": 3.00, "days_overdue": 3},
    ):
        report = ls.get_patron_status_report("123456")

    assert report["books_borrowed_count"] == 1
    assert report["total_late_fees"] == 3.00
    assert report["currently_borrowed"][0]["late_fee"] == 3.00
