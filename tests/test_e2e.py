"""
E2E Browser Tests for Library Management System
"""

import pytest
from playwright.sync_api import Page, expect
import subprocess
import time
import signal
import os
import socket
import requests


def is_server_ready(url, max_retries=30, delay=0.5):
    """Check if the Flask server is ready to accept connections."""
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=1)
            if response.status_code in [200, 302, 404]:  # Server is responding
                return True
        except requests.exceptions.RequestException:
            time.sleep(delay)
    return False


@pytest.fixture(scope="module")
def flask_server():
    """
    Start Flask server as a subprocess for E2E testing.
    """
    # Start Flask server in background
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    
    process = subprocess.Popen(
        ['python', 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        preexec_fn=os.setsid if os.name != 'nt' else None
    )
    
    # Wait for server to be ready
    if not is_server_ready("http://localhost:5000"):
        process.terminate()
        raise RuntimeError("Flask server failed to start within timeout period")
    
    print("\n✓ Flask server is ready")
    
    yield process
    
    # Cleanup: Stop Flask server after tests
    try:
        if os.name == 'nt':  # Windows
            process.terminate()
        else:  # Unix/Linux/Mac
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=5)
    except:
        process.kill()


@pytest.fixture(scope="module")
def app_url():
    """Base URL for the Flask application."""
    return "http://localhost:5000"


@pytest.mark.e2e
def test_add_book_and_verify_in_catalog(page: Page, flask_server, app_url):
    """
    Add a new book and verify it appears in the catalog.
    """
    # Step 1: Navigate to Add Book page
    page.goto(f"{app_url}/add_book")
    
    # Verify we're on the correct page
    expect(page.locator("h2")).to_contain_text("Add New Book")
    
    # Step 2: Fill in the form with book details
    unique_isbn = f"978123456{int(time.time()) % 10000:04d}"  # Generate unique ISBN
    test_title = "The Great Gatsby - E2E Test"
    test_author = "F. Scott Fitzgerald"
    test_copies = "5"
    
    page.fill("#title", test_title)
    page.fill("#author", test_author)
    page.fill("#isbn", unique_isbn)
    page.fill("#total_copies", test_copies)
    
    # Step 3: Submit the form
    page.click("button[type='submit']")
    
    # Step 4: Verify redirect to catalog page
    expect(page).to_have_url(f"{app_url}/catalog")
    
    # Step 5: Verify success message appears
    success_message = page.locator(".flash-success")
    expect(success_message).to_be_visible()
    expect(success_message).to_contain_text("successfully added to the catalog")
    
    # Step 6: Verify the book appears in the catalog table
    # Check that the title appears in the table
    expect(page.locator("table")).to_contain_text(test_title)
    expect(page.locator("table")).to_contain_text(test_author)
    expect(page.locator("table")).to_contain_text(unique_isbn)
    
    # Verify availability shows correct number of copies
    expect(page.locator("table")).to_contain_text(f"{test_copies}/{test_copies} Available")


@pytest.mark.e2e
def test_borrow_book_flow(page: Page, flask_server, app_url):
    """
    Borrow a book from the catalog.
    """
    # Step 1: First add a book to ensure we have one to borrow
    page.goto(f"{app_url}/add_book")
    
    unique_isbn = f"978999999{int(time.time()) % 10000:04d}"
    page.fill("#title", "Test Book for Borrowing")
    page.fill("#author", "Test Author")
    page.fill("#isbn", unique_isbn)
    page.fill("#total_copies", "2")
    page.click("button[type='submit']")
    
    # Step 2: Navigate to catalog and verify we're on the catalog page
    page.goto(f"{app_url}/catalog")
    expect(page.locator("h2")).to_contain_text("Book Catalog")
    
    # Step 3: Find a book with "Available" status (preferably the one we just added)
    available_row = page.locator("tr:has-text('Available')").first
    expect(available_row).to_be_visible()
    
    # Get the initial availability text (e.g., "2/2 Available")
    initial_availability = available_row.locator(".status-available").text_content()
    initial_available_count = int(initial_availability.split('/')[0])
    
    # Step 4 & 5: Enter patron ID and click Borrow button
    patron_id = "789012"  # Valid 6-digit patron ID
    available_row.locator("input[name='patron_id']").fill(patron_id)
    available_row.locator("button:has-text('Borrow')").click()
    
    # Step 6: Verify success message
    success_message = page.locator(".flash-success")
    expect(success_message).to_be_visible()
    expect(success_message).to_contain_text("Successfully borrowed")
    
    # Step 7: Verify the page still shows the catalog
    expect(page.locator("h2")).to_contain_text("Book Catalog")


@pytest.mark.e2e
def test_navigation_links(page: Page, flask_server, app_url):
    """
    Test navigation between different pages.
    """
    # Start at catalog
    page.goto(f"{app_url}/catalog")
    expect(page.locator("h2")).to_contain_text("Book Catalog")
    
    # Navigate to Add Book
    page.click("a:has-text('Add Book')")
    expect(page).to_have_url(f"{app_url}/add_book")
    expect(page.locator("h2")).to_contain_text("Add New Book")
    
    # Navigate back to Catalog
    page.click("a:has-text('Catalog')")
    expect(page).to_have_url(f"{app_url}/catalog")
    
    # Navigate to Return Book
    page.click("a:has-text('Return Book')")
    expect(page).to_have_url(f"{app_url}/return")
    expect(page.locator("h2")).to_contain_text("Return Book")
    
    # Navigate to Patron Status
    page.click("a:has-text('Patron Status')")
    expect(page).to_have_url(f"{app_url}/patron-status")
    expect(page.locator("h2")).to_contain_text("Patron Status")
    
    # Navigate to Search
    page.click("a:has-text('Search')")
    expect(page).to_have_url(f"{app_url}/search")
    expect(page.locator("h2")).to_contain_text("Search Books")

