from itertools import product
from lib2to3.fixes.fix_input import context

from behave import given, when, then
from app.eshop import Product, ShoppingCart

@when('I create product with availability "{available_amount}", name "{name}" and price "{price}"')
def create_product(context, available_amount, name, price):
    try:
        context.product = Product(available_amount = int(available_amount), name = str(name), price = float(price))
        context.create_successfully = True
    except ValueError:
        context.create_successfully = False
    except TypeError:
        context.create_successfully = False

@then("Failure to create a product")
def create_failed(context):
    assert context.create_successfully == False
@when('I create product with availability "{available_amount}", name "{name}" and None price')
def create_product_with_none_price(context, available_amount, name):
    create_product(context, available_amount, name, None)


@when('I check the product availability amount for "{available_amount}"')
def check_available_amount(context, available_amount):
    context.available_check = context.product.is_available(int(available_amount))

@then("The product is not available in the specified quantity")
def product_not_has_available_amount(context):
    assert context.available_check == False

@when('I buy "{available_amount}" items')
def product_buy_amount(context, available_amount):
    context.product.buy(int(available_amount))

@then('The product availability has to be "{available_amount}"')
def assert_product_available_amount(context, available_amount):
    assert context.product.available_amount == int(available_amount)


@given('The product has name of "{name}"')
def create_product_with_name(context, name):
    context.product = Product(name=str(name), price=float(123), available_amount=int(123))

@when('I check the product name for the second product name')
def check_product_name(context):
    context.check_product_name = context.product.__eq__(context.second_product)

@then("The product equals with other product")
def assert_product_name(context):
    assert context.check_product_name == True

@given('The second product has name of "{name}"')
def create_second_product_with_name(context, name):
    context.second_product = Product(name=str(name), price=float(123), available_amount=int(123))

@given('The product has price of "{price}"')
def create_product_with_price(context, price):
    context.product = Product(name=str("123"), price=float(price), available_amount=int(123))
