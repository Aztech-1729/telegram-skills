import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from payment_ledger import PaymentLedger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "ledger.db"
        self.ledger = PaymentLedger(self.path)
        self.ledger.create_order("order-1", 101, 100, 25, expires=2000)

    def tearDown(self):
        self.temp.cleanup()

    def test_checkout_price_user_currency_and_expiry(self):
        self.assertTrue(self.ledger.validate_checkout("order-1", 101, "XTR", 100, now=1000))
        for user, currency, amount, now in [(202, "XTR", 100, 1000), (101, "USD", 100, 1000),
                                             (101, "XTR", 99, 1000), (101, "XTR", 100, 2000)]:
            self.assertFalse(self.ledger.validate_checkout("order-1", user, currency, amount, now=now))

    def test_concurrent_duplicates_persist_without_double_credit(self):
        def accept(_):
            return PaymentLedger(self.path).accept_payment("charge-1", "order-1", 101, "XTR", 100)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(accept, range(8)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(PaymentLedger(self.path).balance(101), 25)
        self.assertFalse(self.ledger.validate_checkout("order-1", 101, "XTR", 100, now=1000))

    def test_mismatches_rollback_and_conflicting_replay(self):
        with self.assertRaises(ValueError):
            self.ledger.accept_payment("bad-charge", "order-1", 202, "XTR", 100)
        self.assertEqual(self.ledger.balance(101), 0)
        self.assertTrue(self.ledger.accept_payment("charge-1", "order-1", 101, "XTR", 100))
        for charge, user, amount in [("charge-1", 202, 100), ("charge-1", 101, 101), ("charge-2", 101, 100)]:
            with self.assertRaises(ValueError):
                self.ledger.accept_payment(charge, "order-1", user, "XTR", amount)
        self.assertEqual(self.ledger.balance(101), 25)

    def test_refund_confirmation_is_idempotent_and_user_bound(self):
        self.ledger.accept_payment("charge-1", "order-1", 101, "XTR", 100)
        with self.assertRaises(ValueError):
            self.ledger.record_completed_refund("charge-1", 202)
        self.assertTrue(self.ledger.record_completed_refund("charge-1", 101))
        self.assertFalse(self.ledger.record_completed_refund("charge-1", 101))
        self.assertFalse(self.ledger.accept_payment("charge-1", "order-1", 101, "XTR", 100))
        self.assertEqual(PaymentLedger(self.path).balance(101), 0)


if __name__ == "__main__":
    unittest.main()
