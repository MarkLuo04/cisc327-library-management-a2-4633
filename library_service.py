"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books
)

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)
    
    if current_borrowed >= 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Process book return by a patron.
    Implements R4: Book Return Processing
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to return
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    # Verify the book was borrowed by this patron
    from database import get_db_connection
    conn = get_db_connection()
    borrow_record = conn.execute('''
        SELECT * FROM borrow_records 
        WHERE patron_id = ? AND book_id = ? AND return_date IS NULL
    ''', (patron_id, book_id)).fetchone()
    conn.close()
    
    if not borrow_record:
        return False, "No active borrow record found for this patron and book."
    
    # Update return date
    return_date = datetime.now()
    update_success = update_borrow_record_return_date(patron_id, book_id, return_date)
    if not update_success:
        return False, "Database error occurred while updating return date."
    
    # Update available copies
    availability_success = update_book_availability(book_id, 1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    # Calculate late fee
    late_fee_info = calculate_late_fee_for_book(patron_id, book_id)
    fee_amount = late_fee_info.get('fee_amount', 0.00)
    days_overdue = late_fee_info.get('days_overdue', 0)
    
    # Build return message
    message = f'Successfully returned "{book["title"]}".'
    if fee_amount > 0:
        message += f' Late fee: ${fee_amount:.2f} ({days_overdue} days overdue).'
    else:
        message += ' No late fees.'
    
    return True, message

def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculate late fees for a specific book.
    Implements R5: Late Fee Calculation API
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book
        
    Returns:
        dict: {
            'fee_amount': float (capped at $15.00),
            'days_overdue': int,
            'status': str
        }
    """
    from database import get_db_connection
    
    # Get the borrow record
    conn = get_db_connection()
    borrow_record = conn.execute('''
        SELECT * FROM borrow_records 
        WHERE patron_id = ? AND book_id = ?
        ORDER BY borrow_date DESC
        LIMIT 1
    ''', (patron_id, book_id)).fetchone()
    conn.close()
    
    if not borrow_record:
        return {
            'fee_amount': 0.00,
            'days_overdue': 0,
            'status': 'No borrow record found'
        }
    
    # Parse dates
    due_date = datetime.fromisoformat(borrow_record['due_date'])
    
    # Use return_date if book has been returned, otherwise use current date
    if borrow_record['return_date']:
        check_date = datetime.fromisoformat(borrow_record['return_date'])
    else:
        check_date = datetime.now()
    
    # Calculate days overdue
    days_overdue = (check_date - due_date).days
    
    # If not overdue, no fee
    if days_overdue <= 0:
        return {
            'fee_amount': 0.00,
            'days_overdue': 0,
            'status': 'Not overdue'
        }
    
    # Calculate fee based on tiered structure
    # $0.50/day for first 7 days overdue
    # $1.00/day for each additional day after 7 days
    # Maximum $15.00 per book
    
    fee_amount = 0.00
    
    if days_overdue <= 7:
        # First 7 days: $0.50 per day
        fee_amount = days_overdue * 0.50
    else:
        # First 7 days at $0.50, remaining days at $1.00
        fee_amount = (7 * 0.50) + ((days_overdue - 7) * 1.00)
    
    # Cap at $15.00
    if fee_amount > 15.00:
        fee_amount = 15.00
    
    return {
        'fee_amount': round(fee_amount, 2),
        'days_overdue': days_overdue,
        'status': 'Overdue' if days_overdue > 0 else 'Not overdue'
    }

def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog.
    Implements R6: Book Search Functionality
    
    Args:
        search_term: The term to search for
        search_type: Type of search ('title', 'author', 'isbn')
        
    Returns:
        list: List of books matching the search criteria
    """
    from database import get_db_connection
    
    if not search_term:
        return []
    
    conn = get_db_connection()
    
    # Validate search type
    valid_types = ['title', 'author', 'isbn']
    if search_type not in valid_types:
        conn.close()
        return []
    
    # Search based on type
    if search_type == 'isbn':
        # Exact matching for ISBN
        books = conn.execute('''
            SELECT * FROM books 
            WHERE isbn = ?
            ORDER BY title
        ''', (search_term,)).fetchall()
    elif search_type == 'title':
        # Partial case-insensitive matching for title
        books = conn.execute('''
            SELECT * FROM books 
            WHERE LOWER(title) LIKE LOWER(?)
            ORDER BY title
        ''', (f'%{search_term}%',)).fetchall()
    elif search_type == 'author':
        # Partial case-insensitive matching for author
        books = conn.execute('''
            SELECT * FROM books 
            WHERE LOWER(author) LIKE LOWER(?)
            ORDER BY title
        ''', (f'%{search_term}%',)).fetchall()
    else:
        conn.close()
        return []
    
    conn.close()
    
    # Convert to list of dictionaries
    return [dict(book) for book in books]

def get_patron_status_report(patron_id: str) -> Dict:
    """
    Get status report for a patron.
    Implements R7: Patron Status Report
    
    Args:
        patron_id: 6-digit library card ID
        
    Returns:
        dict: {
            'currently_borrowed': List of currently borrowed books with due dates,
            'total_late_fees': Total late fees owed,
            'books_borrowed_count': Number of books currently borrowed,
            'borrowing_history': All borrowing records for this patron
        }
    """
    from database import get_db_connection, get_patron_borrowed_books
    
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {}
    
    # Get currently borrowed books
    currently_borrowed = get_patron_borrowed_books(patron_id)
    
    # Format currently borrowed books with due dates
    borrowed_books_list = []
    total_late_fees = 0.00
    
    for book in currently_borrowed:
        late_fee_info = calculate_late_fee_for_book(patron_id, book['book_id'])
        fee = late_fee_info.get('fee_amount', 0.00)
        total_late_fees += fee
        
        borrowed_books_list.append({
            'book_id': book['book_id'],
            'title': book['title'],
            'author': book['author'],
            'borrow_date': book['borrow_date'].strftime('%Y-%m-%d'),
            'due_date': book['due_date'].strftime('%Y-%m-%d'),
            'is_overdue': book['is_overdue'],
            'late_fee': fee
        })
    
    # Get borrowing history (all records, including returned books)
    conn = get_db_connection()
    history_records = conn.execute('''
        SELECT br.*, b.title, b.author 
        FROM borrow_records br 
        JOIN books b ON br.book_id = b.id 
        WHERE br.patron_id = ?
        ORDER BY br.borrow_date DESC
    ''', (patron_id,)).fetchall()
    conn.close()
    
    borrowing_history = []
    for record in history_records:
        # Parse dates and format them properly
        from datetime import datetime
        borrow_date_str = record['borrow_date']
        if isinstance(borrow_date_str, str):
            borrow_date_obj = datetime.fromisoformat(borrow_date_str)
            borrow_date_formatted = borrow_date_obj.strftime('%Y-%m-%d')
        else:
            borrow_date_formatted = borrow_date_str.strftime('%Y-%m-%d') if borrow_date_str else ''
        
        return_date_formatted = None
        if record['return_date']:
            return_date_str = record['return_date']
            if isinstance(return_date_str, str):
                return_date_obj = datetime.fromisoformat(return_date_str)
                return_date_formatted = return_date_obj.strftime('%Y-%m-%d')
            else:
                return_date_formatted = return_date_str.strftime('%Y-%m-%d')
        
        history_entry = {
            'book_id': record['book_id'],
            'title': record['title'],
            'author': record['author'],
            'borrow_date': borrow_date_formatted,
            'due_date': record['due_date'],
            'return_date': return_date_formatted,
            'status': 'Returned' if record['return_date'] else 'Borrowed'
        }
        borrowing_history.append(history_entry)
    
    return {
        'currently_borrowed': borrowed_books_list,
        'total_late_fees': round(total_late_fees, 2),
        'books_borrowed_count': len(borrowed_books_list),
        'borrowing_history': borrowing_history
    }
