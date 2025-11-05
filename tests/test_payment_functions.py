import pytest
from unittest.mock import Mock
from services.library_service import pay_late_fees, refund_late_fee_payment
from services.payment_service import PaymentGateway


# Tests for pay_late_fees() function
class TestPayLateFees:
    """Test suite for pay_late_fees() using mocking and stubbing."""
    
    def test_successful_payment(self, mocker):
        """
        Test successful payment processing with valid patron and late fees.
        Uses STUBBING for database functions and MOCKING for payment gateway.
        """
        # STUB: Provide fake late fee data without verification
        mock_fee_info = {
            'fee_amount': 5.50,
            'days_overdue': 5,
            'status': 'Overdue'
        }
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value=mock_fee_info
        )
        
        # STUB: Provide fake book data
        mock_book = {
            'id': 1,
            'title': 'Test Book',
            'author': 'Test Author',
            'isbn': '1234567890123'
        }
        mocker.patch(
            'services.library_service.get_book_by_id',
            return_value=mock_book
        )
        
        # MOCK: Create mock payment gateway with expected behavior
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (
            True, 
            "txn_123456_success", 
            "Payment processed successfully"
        )
        
        # Execute function
        success, message, transaction_id = pay_late_fees(
            "123456", 1, mock_gateway
        )
        
        # Verify results
        assert success is True
        assert "Payment successful!" in message
        assert transaction_id == "txn_123456_success"
        
        # VERIFY MOCK: Ensure payment gateway was called correctly
        mock_gateway.process_payment.assert_called_once_with(
            patron_id="123456",
            amount=5.50,
            description="Late fees for 'Test Book'"
        )
    
    def test_payment_declined_by_gateway(self, mocker):
        """
        Test payment declined by external gateway.
        Mock should return failure but still be called once.
        """
        # STUB: Provide fake late fee data
        mock_fee_info = {
            'fee_amount': 10.00,
            'days_overdue': 10,
            'status': 'Overdue'
        }
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value=mock_fee_info
        )
        
        # STUB: Provide fake book data
        mock_book = {
            'id': 2,
            'title': 'Expensive Book',
            'author': 'Rich Author',
            'isbn': '9876543210987'
        }
        mocker.patch(
            'services.library_service.get_book_by_id',
            return_value=mock_book
        )
        
        # MOCK: Payment gateway declines transaction
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (
            False,
            None,
            "Insufficient funds"
        )
        
        # Execute function
        success, message, transaction_id = pay_late_fees(
            "654321", 2, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Payment failed: Insufficient funds" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Gateway should still be called
        mock_gateway.process_payment.assert_called_once()
    
    def test_invalid_patron_id_too_short(self, mocker):
        """
        Test invalid patron ID (too short).
        Mock should NOT be called since validation fails early.
        """
        # MOCK: Create gateway that should NOT be called
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with invalid patron ID (5 digits instead of 6)
        success, message, transaction_id = pay_late_fees(
            "12345", 1, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Invalid patron ID" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Payment gateway should NOT be called
        mock_gateway.process_payment.assert_not_called()
    
    def test_invalid_patron_id_non_numeric(self, mocker):
        """
        Test invalid patron ID (contains non-numeric characters).
        Mock should NOT be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with non-numeric patron ID
        success, message, transaction_id = pay_late_fees(
            "ABC123", 1, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Invalid patron ID" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Payment gateway should NOT be called
        mock_gateway.process_payment.assert_not_called()
    
    def test_invalid_patron_id_empty(self, mocker):
        """
        Test empty patron ID.
        Mock should NOT be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with empty patron ID
        success, message, transaction_id = pay_late_fees(
            "", 1, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Invalid patron ID" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Payment gateway should NOT be called
        mock_gateway.process_payment.assert_not_called()
    
    def test_zero_late_fees(self, mocker):
        """
        Test when there are no late fees to pay.
        Mock should NOT be called since no payment is needed.
        """
        # STUB: Return zero late fees
        mock_fee_info = {
            'fee_amount': 0.00,
            'days_overdue': 0,
            'status': 'Not overdue'
        }
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value=mock_fee_info
        )
        
        # MOCK: Gateway should not be called
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute function
        success, message, transaction_id = pay_late_fees(
            "123456", 1, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "No late fees to pay" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Payment gateway should NOT be called for zero fees
        mock_gateway.process_payment.assert_not_called()
    
    def test_book_not_found(self, mocker):
        """
        Test when book doesn't exist in database.
        Mock should NOT be called since book validation fails.
        """
        # STUB: Return valid late fees
        mock_fee_info = {
            'fee_amount': 7.50,
            'days_overdue': 7,
            'status': 'Overdue'
        }
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value=mock_fee_info
        )
        
        # STUB: Book not found
        mocker.patch(
            'services.library_service.get_book_by_id',
            return_value=None
        )
        
        # MOCK: Gateway should not be called
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute function
        success, message, transaction_id = pay_late_fees(
            "123456", 999, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Book not found" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Payment gateway should NOT be called
        mock_gateway.process_payment.assert_not_called()
    
    def test_network_error_exception_handling(self, mocker):
        """
        Test handling of network errors from payment gateway.
        Gateway raises exception which should be caught and handled.
        """
        # STUB: Provide fake late fee data
        mock_fee_info = {
            'fee_amount': 12.50,
            'days_overdue': 15,
            'status': 'Overdue'
        }
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value=mock_fee_info
        )
        
        # STUB: Provide fake book data
        mock_book = {
            'id': 3,
            'title': 'Network Test Book',
            'author': 'Test Author',
            'isbn': '1111222233334'
        }
        mocker.patch(
            'services.library_service.get_book_by_id',
            return_value=mock_book
        )
        
        # MOCK: Gateway raises exception (simulating network error)
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.side_effect = Exception(
            "Network timeout"
        )
        
        # Execute function
        success, message, transaction_id = pay_late_fees(
            "123456", 3, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Payment processing error" in message
        assert "Network timeout" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Gateway was called but raised exception
        mock_gateway.process_payment.assert_called_once()
    
    def test_missing_fee_info(self, mocker):
        """
        Test when calculate_late_fee_for_book returns invalid data.
        Mock should NOT be called.
        """
        # STUB: Return None (database error)
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value=None
        )
        
        # MOCK: Gateway should not be called
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute function
        success, message, transaction_id = pay_late_fees(
            "123456", 1, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Unable to calculate late fees" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Payment gateway should NOT be called
        mock_gateway.process_payment.assert_not_called()
    
    def test_fee_info_missing_amount_key(self, mocker):
        """
        Test when fee_info dict doesn't have 'fee_amount' key.
        Mock should NOT be called.
        """
        # STUB: Return incomplete fee info
        mock_fee_info = {
            'days_overdue': 5,
            'status': 'Overdue'
            # Missing 'fee_amount' key
        }
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value=mock_fee_info
        )
        
        # MOCK: Gateway should not be called
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute function
        success, message, transaction_id = pay_late_fees(
            "123456", 1, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Unable to calculate late fees" in message
        assert transaction_id is None
        
        # VERIFY MOCK: Payment gateway should NOT be called
        mock_gateway.process_payment.assert_not_called()


# Tests for refund_late_fee_payment()
class TestRefundLateFeePayment:
    """Test suite for refund_late_fee_payment() using mocking."""
    
    def test_successful_refund(self):
        """
        Test successful refund processing.
        MOCK should be called with correct parameters.
        """
        # MOCK: Create mock payment gateway
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.refund_payment.return_value = (
            True,
            "Refund of $5.50 processed successfully. Refund ID: refund_txn_123"
        )
        
        # Execute function
        success, message = refund_late_fee_payment(
            "txn_123456_test", 5.50, mock_gateway
        )
        
        # Verify results
        assert success is True
        assert "Refund of $5.50 processed successfully" in message
        
        # VERIFY MOCK: Ensure refund was called correctly
        mock_gateway.refund_payment.assert_called_once_with(
            "txn_123456_test", 5.50
        )
    
    def test_refund_declined_by_gateway(self):
        """
        Test refund declined by payment gateway.
        Mock should be called but return failure.
        """
        # MOCK: Gateway declines refund
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.refund_payment.return_value = (
            False,
            "Transaction already refunded"
        )
        
        # Execute function
        success, message = refund_late_fee_payment(
            "txn_999999_test", 10.00, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Refund failed: Transaction already refunded" in message
        
        # VERIFY MOCK: Gateway should be called
        mock_gateway.refund_payment.assert_called_once()
    
    def test_invalid_transaction_id_no_prefix(self):
        """
        Test invalid transaction ID (missing 'txn_' prefix).
        Mock should NOT be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with invalid transaction ID
        success, message = refund_late_fee_payment(
            "invalid_123456", 5.00, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Invalid transaction ID" in message
        
        # VERIFY MOCK: Gateway should NOT be called
        mock_gateway.refund_payment.assert_not_called()
    
    def test_invalid_transaction_id_empty(self):
        """
        Test empty transaction ID.
        Mock should NOT be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with empty transaction ID
        success, message = refund_late_fee_payment(
            "", 5.00, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Invalid transaction ID" in message
        
        # VERIFY MOCK: Gateway should NOT be called
        mock_gateway.refund_payment.assert_not_called()
    
    def test_invalid_amount_negative(self):
        """
        Test negative refund amount.
        Mock should NOT be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with negative amount
        success, message = refund_late_fee_payment(
            "txn_123456_test", -5.00, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Refund amount must be greater than 0" in message
        
        # VERIFY MOCK: Gateway should NOT be called
        mock_gateway.refund_payment.assert_not_called()
    
    def test_invalid_amount_zero(self):
        """
        Test zero refund amount.
        Mock should NOT be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with zero amount
        success, message = refund_late_fee_payment(
            "txn_123456_test", 0.00, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Refund amount must be greater than 0" in message
        
        # VERIFY MOCK: Gateway should NOT be called
        mock_gateway.refund_payment.assert_not_called()
    
    def test_invalid_amount_exceeds_maximum(self):
        """
        Test refund amount exceeding $15.00 maximum.
        Mock should NOT be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        
        # Execute with amount over maximum
        success, message = refund_late_fee_payment(
            "txn_123456_test", 20.00, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Refund amount exceeds maximum late fee" in message
        
        # VERIFY MOCK: Gateway should NOT be called
        mock_gateway.refund_payment.assert_not_called()
    
    def test_invalid_amount_exactly_maximum_allowed(self):
        """
        Test refund amount exactly at $15.00 maximum (should be allowed).
        Mock SHOULD be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.refund_payment.return_value = (
            True,
            "Refund of $15.00 processed successfully"
        )
        
        # Execute with maximum allowed amount
        success, message = refund_late_fee_payment(
            "txn_123456_test", 15.00, mock_gateway
        )
        
        # Verify results
        assert success is True
        assert "Refund of $15.00 processed successfully" in message
        
        # VERIFY MOCK: Gateway SHOULD be called for valid maximum
        mock_gateway.refund_payment.assert_called_once_with(
            "txn_123456_test", 15.00
        )
    
    def test_refund_exception_handling(self):
        """
        Test handling of exceptions from payment gateway.
        Gateway raises exception which should be caught.
        """
        # MOCK: Gateway raises exception
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.refund_payment.side_effect = Exception(
            "Connection refused"
        )
        
        # Execute function
        success, message = refund_late_fee_payment(
            "txn_123456_test", 8.00, mock_gateway
        )
        
        # Verify results
        assert success is False
        assert "Refund processing error" in message
        assert "Connection refused" in message
        
        # VERIFY MOCK: Gateway was called but raised exception
        mock_gateway.refund_payment.assert_called_once()
    
    def test_refund_with_valid_small_amount(self):
        """
        Test refund with small valid amount (boundary test).
        Mock should be called.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.refund_payment.return_value = (
            True,
            "Refund of $0.50 processed successfully"
        )
        
        # Execute with small valid amount
        success, message = refund_late_fee_payment(
            "txn_123456_test", 0.50, mock_gateway
        )
        
        # Verify results
        assert success is True
        
        # VERIFY MOCK: Gateway should be called
        mock_gateway.refund_payment.assert_called_once_with(
            "txn_123456_test", 0.50
        )
    
    def test_verify_mock_called_with_exact_parameters(self):
        """
        Detailed test to verify exact parameter passing to mock.
        Demonstrates assert_called_with() usage.
        """
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.refund_payment.return_value = (True, "Success")
        
        # Execute
        refund_late_fee_payment("txn_999888_test", 12.75, mock_gateway)
        
        # VERIFY: Exact parameters with assert_called_with
        mock_gateway.refund_payment.assert_called_with(
            "txn_999888_test", 12.75
        )
        
        # Also verify it was called exactly once
        assert mock_gateway.refund_payment.call_count == 1
