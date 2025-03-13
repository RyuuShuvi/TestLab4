from behave import given, when, then
from app.eshop import Product, ShoppingCart


@given('The product has availability of "{availability}"')
def create_product_for_cart(context, availability):
    context.product = Product(name=str("any"), price=float(123), available_amount=int(availability))

@given('An empty shopping cart')
def empty_cart(context):
    context.cart = ShoppingCart()

@when('I add product to the cart in amount "{product_amount}"')
def add_product(context, product_amount):
    try:
        context.cart.add_product(context.product, int(product_amount))
        context.add_successfully = True
    except ValueError:
        context.add_successfully = False

@then("Product is added to the cart successfully")
def add_successful(context):
    assert context.add_successfully == True

@then("Product is not added to cart successfully")
def add_failed(context):
    assert context.add_successfully == False

@then('The total price has to be "{total_price}"')
def assert_total_price(context, total_price):
    total = context.cart.calculate_total()
    assert total == float(total_price)

@when("I remove product form cart")
def remove_product_from_cart(context):
    context.remove_product = context.cart.remove_product(context.product)

@then("Product is removed from cart successfully")
def product_removed_successful(context):
    assert context.remove_product == True

@when("I find the product in the cart")
def find_product_in_cart(context):
    context.founded_product = context.cart.contains_product(context.product)


@then("The found product is the same as the added product")
def assert_found_and_contains_products(context):
    assert context.founded_product == True
