# Unit tests for payment gateway functions using mocking and stubbing

import pytest
from unittest.mock import Mock
from services.library_service import pay_late_fees, refund_late_fee_payment
from services.payment_service import PaymentGateway


class TestPayLateFees:
    
    # Test successful payment processing with valid patron and late fees
    def test_successful_payment(self, mocker):
        # Stub late fee calculation
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value={'fee_amount': 5.50, 'days_overdue': 5, 'status': 'Overdue'}
        )
        
        # Stub book lookup
        mocker.patch(
            'services.library_service.get_book_by_id',
            return_value={'id': 1, 'title': 'Test Book', 'author': 'Test Author', 'isbn': '1234567890123'}
        )
        
        # Mock payment gateway
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (True, "txn_123456_success", "Payment processed successfully")
        
        success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
        
        assert success is True
        assert "Payment successful!" in message
        assert transaction_id == "txn_123456_success"
        mock_gateway.process_payment.assert_called_once_with(
            patron_id="123456",
            amount=5.50,
            description="Late fees for 'Test Book'"
        )
    
    # Test payment declined by gateway
    def test_payment_declined_by_gateway(self, mocker):
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value={'fee_amount': 10.00, 'days_overdue': 10, 'status': 'Overdue'}
        )
        mocker.patch(
            'services.library_service.get_book_by_id',
            return_value={'id': 2, 'title': 'Expensive Book', 'author': 'Rich Author', 'isbn': '9876543210987'}
        )
        
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (False, None, "Insufficient funds")
        
        success, message, transaction_id = pay_late_fees("654321", 2, mock_gateway)
        
        assert success is False
        assert "Payment failed: Insufficient funds" in message
        assert transaction_id is None
        mock_gateway.process_payment.assert_called_once()
    
    # Test invalid patron ID (verify mock NOT called)
    def test_invalid_patron_id(self):
        mock_gateway = Mock(spec=PaymentGateway)
        
        success, message, transaction_id = pay_late_fees("12345", 1, mock_gateway)
        
        assert success is False
        assert "Invalid patron ID" in message
        assert transaction_id is None
        mock_gateway.process_payment.assert_not_called()
    
    # Test no payment when late fees are zero (verify mock NOT called)
    def test_zero_late_fees(self, mocker):
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value={'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Not overdue'}
        )
        
        mock_gateway = Mock(spec=PaymentGateway)
        
        success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
        
        assert success is False
        assert "No late fees to pay" in message
        assert transaction_id is None
        mock_gateway.process_payment.assert_not_called()
    
    # Test handling of network errors from payment gateway
    def test_network_error_exception_handling(self, mocker):
        mocker.patch(
            'services.library_service.calculate_late_fee_for_book',
            return_value={'fee_amount': 12.50, 'days_overdue': 15, 'status': 'Overdue'}
        )
        mocker.patch(
            'services.library_service.get_book_by_id',
            return_value={'id': 3, 'title': 'Network Test Book', 'author': 'Test Author', 'isbn': '1111222233334'}
        )
        
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.side_effect = Exception("Network timeout")
        
        success, message, transaction_id = pay_late_fees("123456", 3, mock_gateway)
        
        assert success is False
        assert "Payment processing error" in message
        assert "Network timeout" in message
        assert transaction_id is None
        mock_gateway.process_payment.assert_called_once()


class TestRefundLateFeePayment:
    
    # Test successful refund processing
    def test_successful_refund(self):
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.refund_payment.return_value = (
            True,
            "Refund of $5.50 processed successfully. Refund ID: refund_txn_123"
        )
        
        success, message = refund_late_fee_payment("txn_123456_test", 5.50, mock_gateway)
        
        assert success is True
        assert "Refund of $5.50 processed successfully" in message
        mock_gateway.refund_payment.assert_called_once_with("txn_123456_test", 5.50)
    
    # Test invalid transaction ID rejection
    def test_invalid_transaction_id(self):
        mock_gateway = Mock(spec=PaymentGateway)
        
        success, message = refund_late_fee_payment("invalid_123456", 5.00, mock_gateway)
        
        assert success is False
        assert "Invalid transaction ID" in message
        mock_gateway.refund_payment.assert_not_called()
    
    # Test invalid refund amount (negative)
    def test_invalid_amount_negative(self):
        mock_gateway = Mock(spec=PaymentGateway)
        
        success, message = refund_late_fee_payment("txn_123456_test", -5.00, mock_gateway)
        
        assert success is False
        assert "Refund amount must be greater than 0" in message
        mock_gateway.refund_payment.assert_not_called()
    
    # Test invalid refund amount (zero)
    def test_invalid_amount_zero(self):
        mock_gateway = Mock(spec=PaymentGateway)
        
        success, message = refund_late_fee_payment("txn_123456_test", 0.00, mock_gateway)
        
        assert success is False
        assert "Refund amount must be greater than 0" in message
        mock_gateway.refund_payment.assert_not_called()
    
    # Test invalid refund amount (exceeds $15 maximum)
    def test_invalid_amount_exceeds_maximum(self):
        mock_gateway = Mock(spec=PaymentGateway)
        
        success, message = refund_late_fee_payment("txn_123456_test", 20.00, mock_gateway)
        
        assert success is False
        assert "Refund amount exceeds maximum late fee" in message
        mock_gateway.refund_payment.assert_not_called()

