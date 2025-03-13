import unittest
from app.eshop import Product, ShoppingCart, Order

from unittest.mock import MagicMock
class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.product = Product(name='Test', price=123.45, available_amount=21)
        self.cart = ShoppingCart()
    def tearDown(self):
        self.cart.remove_product(self.product)
    def test_mock_add_product(self):
        self.product.is_available = MagicMock()
        self.cart.add_product(self.product, 12345)
        self.product.is_available.assert_called_with(12345)
        self.product.is_available.reset_mock()
    def test_add_available_amount(self):
        self.cart.add_product(self.product, 11)
        self.assertEqual(self.cart.contains_product(self.product), True, 'Продукт успішно доданий до корзини')
    def test_add_non_available_amount(self):
        with self.assertRaises(ValueError):
            self.cart.add_product(self.product, 22)
        self.assertEqual(self.cart.contains_product(self.product), False, 'Продукт не доданий до корзини')
# ===================
    def test_remove_product(self):
        self.cart.remove_product(self.product)
        self.assertEqual(self.cart.contains_product(self.product), False, "Продукт видалився з кошику")

    def test_calculate_total(self):
        self.cart.add_product(self.product, 21)
        self.assertAlmostEqual(self.cart.calculate_total(), 2592.45, places=2, msg="Кінцева сума розрахована правильно")

    def test_mock_buy_product_from_cart_order(self):
        self.cart.add_product(self.product, 2)
        self.product.buy = MagicMock()
        self.cart.submit_cart_order()
        self.product.buy.assert_called_with(2)
        self.product.buy.reset_mock()

    def test_create_product_with_wrong_price(self):
        with self.assertRaises(ValueError):
            self.product = Product(name='Test', price=-123.45, available_amount=21)

    def test_create_product_with_wrong_type_price(self):
        with self.assertRaises(TypeError):
            self.product = Product(name='Test', price='one', available_amount=21)

    def test_buy_product(self):
        self.product.buy(3)
        self.assertEqual(self.product.available_amount, 18)

    def test_product_is_not_available(self):
         self.assertEqual(self.product.is_available(25), False)

    def test_cart_contains_product(self):
        self.cart.add_product(self.product, 10)
        self.assertEqual(self.cart.contains_product(self.product), True)

    def test_create_product_with_wrong_available_amount(self):
        with self.assertRaises(ValueError):
            self.product = Product(name='Test', price=123.45, available_amount=-21)

    def test_create_product_with_wrong_name(self):
        with self.assertRaises(ValueError):
            self.product = Product(name='te', price=123.45, available_amount=21)


if __name__ == '__main__':
    unittest.main()
