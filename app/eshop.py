"""E-commerce module containing shopping cart and order functionality."""

import uuid
from typing import Dict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

try:
    from services import ShippingService
except ImportError:
    ShippingService = None  # Fallback for missing service

class Product:
    """Represents a product in the e-commerce system."""

    def __init__(self, name: str, price: float, available_amount: int):
        """Initialize a product with name, price, and available quantity.

        Args:
            name: Product name (min 3 chars)
            price: Product price (> 0)
            available_amount: Available quantity (>= 0)

        Raises:
            TypeError: If types are incorrect
            ValueError: If values are invalid
        """
        if not isinstance(name, str) or not isinstance(price, float) or not isinstance(available_amount, int):
            raise TypeError("Incorrect product field types")
        if price <= 0:
            raise ValueError("Price must be greater than 0")
        if len(name) < 3:
            raise ValueError("The name must have 3 or more characters")
        if available_amount < 0:
            raise ValueError("The available amount must be >= 0")

        self.name = name
        self.price = price
        self.available_amount = available_amount

    def is_available(self, requested_amount: int) -> bool:
        """Check if requested amount is available."""
        return self.available_amount >= requested_amount

    def buy(self, requested_amount: int) -> None:
        """Reduce available amount by requested quantity."""
        self.available_amount -= requested_amount

    def __eq__(self, other) -> bool:
        return self.name == other.name

    def __ne__(self, other) -> bool:
        return self.name != other.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name


class ShoppingCart:
    """Manages a shopping cart with products and quantities."""

    def __init__(self):
        """Initialize an empty shopping cart."""
        self.products: Dict[Product, int] = {}

    def contains_product(self, product: Product) -> bool:
        """Check if product is in cart."""
        return product in self.products

    def calculate_total(self) -> float:
        """Calculate total price of items in cart."""
        return sum(p.price * count for p, count in self.products.items())

    def add_product(self, product: Product, amount: int) -> None:
        """Add product to cart with specified amount."""
        if not product.is_available(amount):
            raise ValueError(f"Product {product} has only {product.available_amount} items")
        self.products[product] = amount

    def remove_product(self, product: Product) -> bool:
        """Remove product from cart."""
        if product in self.products:
            del self.products[product]
            return True
        return False

    def submit_cart_order(self) -> List[str]:
        """Process cart items and return product IDs."""
        product_ids = []
        for product, count in self.products.items():
            product.buy(count)
            product_ids.append(str(product))
        self.products.clear()
        return product_ids


@dataclass
class Order:
    """Represents a customer order with cart and shipping."""
    cart: ShoppingCart
    shipping_service: 'ShippingService'
    order_id: str = str(uuid.uuid4())

    def place_order(self, shipping_type: str, due_date: datetime = None) -> str:
        """Place order and create shipping request."""
        if not due_date:
            due_date = datetime.now(timezone.utc) + timedelta(seconds=3)
        product_ids = self.cart.submit_cart_order()
        print(due_date)
        return self.shipping_service.create_shipping(
            shipping_type, product_ids, self.order_id, due_date
        )


@dataclass
class Shipment:
    """Manages shipping status tracking."""
    shipping_id: str
    shipping_service: 'ShippingService'

    def check_shipping_status(self) -> str:
        """Check current status of shipment."""
        return self.shipping_service.check_status(self.shipping_id)
