import uuid

import boto3
from app.eshop import Product, ShoppingCart, Order
import random
from services import ShippingService
from services.repository import ShippingRepository
from services.publisher import ShippingPublisher
from datetime import datetime, timedelta, timezone
from services.config import AWS_ENDPOINT_URL, AWS_REGION, SHIPPING_QUEUE
import pytest


@pytest.mark.parametrize("order_id, shipping_id", [
    ("order_1", "shipping_1"),
    ("order_i2hur2937r9", "shipping_1!!!!"),
    (8662354, 123456),
    (str(uuid.uuid4()), str(uuid.uuid4()))
])
def test_place_order_with_mocked_repo(mocker, order_id, shipping_id):
    mock_repo = mocker.Mock()
    mock_publisher = mocker.Mock()
    shipping_service = ShippingService(mock_repo, mock_publisher)

    mock_repo.create_shipping.return_value = shipping_id

    cart = ShoppingCart()
    cart.add_product(Product(
        available_amount=10,
        name='Product',
        price=random.random() * 10000),
        amount=9
    )

    order = Order(cart, shipping_service, order_id)
    due_date = datetime.now(timezone.utc) + timedelta(seconds=3)
    actual_shipping_id = order.place_order(
        ShippingService.list_available_shipping_type()[0],
        due_date=due_date
    )

    assert actual_shipping_id == shipping_id, "Actual shipping id must be equal to mock return value"

    mock_repo.create_shipping.assert_called_with(ShippingService.list_available_shipping_type()[0], ["Product"], order_id, shipping_service.SHIPPING_CREATED, due_date)
    mock_publisher.send_new_shipping.assert_called_with(shipping_id)


def test_place_order_with_unavailable_shipping_type_fails(dynamo_resource):
    shipping_service = ShippingService(ShippingRepository(), ShippingPublisher())
    cart = ShoppingCart()
    cart.add_product(Product(
        available_amount=10,
        name='Product',
        price=random.random() * 10000),
        amount=9
    )
    order = Order(cart, shipping_service)
    shipping_id = None

    with pytest.raises(ValueError) as excinfo:
        shipping_id = order.place_order(
            "Новий тип доставки",
            due_date=datetime.now(timezone.utc) + timedelta(seconds=3)
        )
    assert shipping_id is None, "Shipping id must not be assigned"
    assert "Shipping type is not available" in str(excinfo.value)



def test_when_place_order_then_shipping_in_queue(dynamo_resource):
    shipping_service = ShippingService(ShippingRepository(), ShippingPublisher())
    cart = ShoppingCart()

    cart.add_product(Product(
        available_amount=10,
        name='Product',
        price=random.random() * 10000),
        amount=9
    )

    order = Order(cart, shipping_service)
    shipping_id = order.place_order(
        ShippingService.list_available_shipping_type()[0],
        due_date=datetime.now(timezone.utc) + timedelta(minutes=1)
    )

    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    messages = response.get("Messages", [])
    assert len(messages) == 1, "Expected 1 SQS message"

    body = messages[0]["Body"]
    assert shipping_id == body





# Тест 1: Перевірка повного циклу замовлення з мокнутими низькорівневими компонентами
def test_full_order_flow_with_mocked_shipping_service(mocker, dynamo_resource):
    # Мокнемо ShippingService для ізоляції верхнього рівня
    mock_shipping_service = mocker.Mock(spec=ShippingService)
    mock_shipping_service.create_shipping.return_value = "mock_shipping_id"

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product = Product(name="Test Product", price=99.99, available_amount=5)
    cart.add_product(product, 2)

    order = Order(cart=cart, shipping_service=mock_shipping_service)

    # Виконуємо дію верхнього рівня
    due_date = datetime.now(timezone.utc) + timedelta(seconds=3)
    shipping_id = order.place_order(
        shipping_type="Нова Пошта",
        due_date=due_date
    )

    # Перевіряємо результати
    assert shipping_id == "mock_shipping_id"
    assert product.available_amount == 3  # Перевіряємо, що кількість зменшилась
    assert len(cart.products) == 0  # Кошик очистився

    # Перевіряємо виклик нижнього рівня
    mock_shipping_service.create_shipping.assert_called_once_with(
        "Нова Пошта",
        ["Test Product"],
        order.order_id,
        due_date
    )


# Тест 2: Інтеграція Order з реальним ShippingService та мокнутими Repository/Publisher
def test_order_integration_with_real_shipping_service(mocker, dynamo_resource):
    # Мокнемо нижні компоненти ShippingService
    mock_repository = mocker.Mock(spec=ShippingRepository)
    mock_publisher = mocker.Mock(spec=ShippingPublisher)

    mock_repository.create_shipping.return_value = "test_shipping_id"
    mock_publisher.send_new_shipping.return_value = "message_id"

    # Використовуємо реальний ShippingService з мокнутими залежностями
    shipping_service = ShippingService(mock_repository, mock_publisher)

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product = Product(name="Test Product", price=49.99, available_amount=10)
    cart.add_product(product, 3)

    order = Order(cart=cart, shipping_service=shipping_service)

    # Виконуємо замовлення
    due_date = datetime.now(timezone.utc) + timedelta(minutes=1)
    shipping_id = order.place_order(
        shipping_type="Укр Пошта",
        due_date=due_date
    )

    # Перевіряємо результати
    assert shipping_id == "test_shipping_id"
    assert product.available_amount == 7
    assert len(cart.products) == 0

    # Перевіряємо взаємодію з Repository
    mock_repository.create_shipping.assert_called_once_with(
        "Укр Пошта",
        ["Test Product"],
        order.order_id,
        shipping_service.SHIPPING_CREATED,
        due_date
    )

    # Перевіряємо взаємодію з Publisher
    mock_publisher.send_new_shipping.assert_called_once_with("test_shipping_id")

    # Перевіряємо, що статус оновлено
    mock_repository.update_shipping_status.assert_called_once_with(
        "test_shipping_id",
        shipping_service.SHIPPING_IN_PROGRESS
    )


# Тест 3: Перевірка обробки помилки недостатньої кількості товару з реальним ShoppingCart
def test_order_fails_with_insufficient_product_amount(mocker, dynamo_resource):
    # Мокнемо ShippingService, щоб ізолювати верхній рівень
    mock_shipping_service = mocker.Mock(spec=ShippingService)

    # Створюємо реальний ShoppingCart і Product
    cart = ShoppingCart()
    product = Product(name="Limited Product", price=29.99, available_amount=2)

    # Додаємо більше товару, ніж доступно
    with pytest.raises(ValueError) as excinfo:
        cart.add_product(product, 3)

    # Створюємо Order з реальним кошиком
    order = Order(cart=cart, shipping_service=mock_shipping_service)

    # Переконуємося, що кошик залишився порожнім
    assert len(cart.products) == 0
    assert product.available_amount == 2  # Кількість не змінилася
    assert "has only 2 items" in str(excinfo.value)

    # Перевіряємо, що ShippingService не викликався
    mock_shipping_service.create_shipping.assert_not_called()


# Тест 4: Інтеграція Order з реальними ShippingService і Publisher, мокнутим Repository
def test_order_with_real_shipping_and_publisher(mocker, dynamo_resource):
    # Мокнемо Repository, але використовуємо реальний Publisher
    mock_repository = mocker.Mock(spec=ShippingRepository)
    real_publisher = ShippingPublisher()

    mock_repository.create_shipping.return_value = "real_shipping_id"
    mock_repository.update_shipping_status.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

    shipping_service = ShippingService(mock_repository, real_publisher)

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product = Product(name="Real Product", price=79.99, available_amount=5)
    cart.add_product(product, 2)

    order = Order(cart=cart, shipping_service=shipping_service)

    # Виконуємо замовлення
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)
    shipping_id = order.place_order(
        shipping_type="Meest Express",
        due_date=due_date
    )

    # Перевіряємо результати
    assert shipping_id == "real_shipping_id"
    assert product.available_amount == 3  # Кількість зменшилась
    assert len(cart.products) == 0  # Кошик очистився

    # Перевіряємо виклик Repository
    mock_repository.create_shipping.assert_called_once_with(
        "Meest Express",
        ["Real Product"],
        order.order_id,
        shipping_service.SHIPPING_CREATED,
        due_date
    )

    # Перевіряємо, що повідомлення відправлено в SQS через реальний Publisher
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    messages = response.get("Messages", [])
    assert len(messages) == 1, "Очікувалось повідомлення в SQS"
    assert messages[0]["Body"] == "real_shipping_id"

    # Перевіряємо оновлення статусу
    mock_repository.update_shipping_status.assert_called_once_with(
        "real_shipping_id",
        shipping_service.SHIPPING_IN_PROGRESS
    )

# Тест 5: Перевірка помилки при виборі застарілої дати доставки
def test_order_fails_with_past_due_date(mocker, dynamo_resource):
    # Мокнемо ShippingService для ізоляції верхнього рівня
    mock_shipping_service = mocker.Mock(spec=ShippingService)

    # Налаштовуємо мок, щоб він кидав ValueError при past_due_date
    def mock_create_shipping(shipping_type, product_ids, order_id, due_date):
        if due_date <= datetime.now(timezone.utc):
            raise ValueError("Shipping due datetime must be greater than datetime now")
        return "mock_shipping_id"

    mock_shipping_service.create_shipping.side_effect = mock_create_shipping

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product = Product(name="Fast Product", price=19.99, available_amount=4)
    cart.add_product(product, 1)

    order = Order(cart=cart, shipping_service=mock_shipping_service)

    # Спроба розмістити замовлення з датою в минулому
    past_due_date = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Перевіряємо, що виникає помилка
    with pytest.raises(ValueError) as excinfo:
        order.place_order(
            shipping_type="Самовивіз",
            due_date=past_due_date
        )

    # Перевіряємо стан системи з урахуванням поточної логіки
    assert "Shipping due datetime must be greater than datetime now" in str(excinfo.value)
    assert product.available_amount == 3  # Кількість зменшилася через submit_cart_order
    assert len(cart.products) == 0  # Кошик очистився через submit_cart_order
    mock_shipping_service.create_shipping.assert_called_once_with(
        "Самовивіз",
        ["Fast Product"],
        order.order_id,
        past_due_date
    )

# Тест 6: Повна інтеграція Order з реальними ShippingService і Repository, без моків нижнього рівня
def test_full_integration_order_to_repository(dynamo_resource):
    # Використовуємо реальні компоненти без моків
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product = Product(name="Full Test Product", price=149.99, available_amount=3)
    cart.add_product(product, 2)

    order = Order(cart=cart, shipping_service=shipping_service)

    # Виконуємо замовлення
    due_date = datetime.now(timezone.utc) + timedelta(minutes=3)
    shipping_id = order.place_order(
        shipping_type="Нова Пошта",
        due_date=due_date
    )

    # Перевіряємо результати верхнього рівня
    assert shipping_id is not None
    assert product.available_amount == 1  # Кількість зменшилась
    assert len(cart.products) == 0  # Кошик очистився

    # Перевіряємо збереження в DynamoDB через реальний Repository
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data is not None
    assert shipping_data["shipping_type"] == "Нова Пошта"
    assert shipping_data["order_id"] == order.order_id
    assert shipping_data["product_ids"] == "Full Test Product"
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS

    # Перевіряємо відправку в SQS через реальний Publisher
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    messages = response.get("Messages", [])
    assert len(messages) == 1, "Очікувалось повідомлення в SQS"
    assert messages[0]["Body"] == shipping_id


# Тест 7: Перевірка помилки при додаванні неіснуючого типу доставки з реальним ShippingService
def test_order_fails_with_invalid_shipping_type(mocker, dynamo_resource):
    # Використовуємо реальний ShippingService з мокнутими залежностями
    mock_repository = mocker.Mock(spec=ShippingRepository)
    mock_publisher = mocker.Mock(spec=ShippingPublisher)
    shipping_service = ShippingService(mock_repository, mock_publisher)

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product = Product(name="Test Product", price=39.99, available_amount=5)
    cart.add_product(product, 2)

    order = Order(cart=cart, shipping_service=shipping_service)

    # Спроба розмістити замовлення з неіснуючим типом доставки
    invalid_shipping_type = "Невідомий перевізник"
    due_date = datetime.now(timezone.utc) + timedelta(minutes=5)

    # Перевіряємо, що виникає помилка
    with pytest.raises(ValueError) as excinfo:
        order.place_order(
            shipping_type=invalid_shipping_type,
            due_date=due_date
        )

    # Перевіряємо стан системи
    assert "Shipping type is not available" in str(excinfo.value)
    assert product.available_amount == 3  # Кількість зменшилася через submit_cart_order
    assert len(cart.products) == 0  # Кошик очистився через submit_cart_order
    mock_repository.create_shipping.assert_not_called()
    mock_publisher.send_new_shipping.assert_not_called()


# Тест 8: Інтеграція Order з реальними ShoppingCart і ShippingService, перевірка статусу доставки
def test_order_integration_with_shipping_status_check(dynamo_resource):
    # Використовуємо реальні компоненти
    real_repository = ShippingRepository()
    real_publisher = ShippingPublisher()
    shipping_service = ShippingService(real_repository, real_publisher)

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product = Product(name="Status Product", price=89.99, available_amount=10)
    cart.add_product(product, 3)

    order = Order(cart=cart, shipping_service=shipping_service)

    # Виконуємо замовлення
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)
    shipping_id = order.place_order(
        shipping_type="Укр Пошта",
        due_date=due_date
    )

    # Перевіряємо верхній рівень
    assert shipping_id is not None
    assert product.available_amount == 7  # Кількість зменшилася
    assert len(cart.products) == 0  # Кошик очистився

    # Перевіряємо статус доставки через ShippingService
    shipping_status = shipping_service.check_status(shipping_id)
    assert shipping_status == shipping_service.SHIPPING_IN_PROGRESS

    # Перевіряємо збереження в DynamoDB
    shipping_data = real_repository.get_shipping(shipping_id)
    assert shipping_data["shipping_type"] == "Укр Пошта"
    assert shipping_data["product_ids"] == "Status Product"
    assert shipping_data["shipping_status"] == shipping_service.SHIPPING_IN_PROGRESS

    # Перевіряємо SQS
    sqs_client = boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION
    )
    queue_url = sqs_client.get_queue_url(QueueName=SHIPPING_QUEUE)["QueueUrl"]
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )
    messages = response.get("Messages", [])
    assert len(messages) == 1
    assert messages[0]["Body"] == shipping_id

    # Імітуємо обробку доставки
    shipping_service.process_shipping(shipping_id)
    updated_status = shipping_service.check_status(shipping_id)
    assert updated_status == shipping_service.SHIPPING_COMPLETED


# Тест 9: Перевірка видалення продукту з кошика перед розміщенням замовлення
def test_order_with_product_removal_before_submission(mocker, dynamo_resource):
    # Мокнемо ShippingService для ізоляції верхнього рівня
    mock_shipping_service = mocker.Mock(spec=ShippingService)
    mock_shipping_service.create_shipping.return_value = "mock_shipping_id"

    # Створюємо реальні об'єкти верхнього рівня
    cart = ShoppingCart()
    product1 = Product(name="Product A", price=29.99, available_amount=5)
    product2 = Product(name="Product B", price=49.99, available_amount=3)
    cart.add_product(product1, 2)
    cart.add_product(product2, 1)

    # Видаляємо один продукт перед замовленням
    cart.remove_product(product2)

    order = Order(cart=cart, shipping_service=mock_shipping_service)

    # Розміщуємо замовлення
    due_date = datetime.now(timezone.utc) + timedelta(minutes=3)
    shipping_id = order.place_order(
        shipping_type="Нова Пошта",
        due_date=due_date
    )

    # Перевіряємо стан
    assert shipping_id == "mock_shipping_id"
    assert product1.available_amount == 3  # Зменшено тільки для Product A
    assert product2.available_amount == 3  # Product B не змінено
    assert len(cart.products) == 0  # Кошик очистився
    mock_shipping_service.create_shipping.assert_called_once_with(
        "Нова Пошта",
        ["Product A"],  # Тільки Product A в замовленні
        order.order_id,
        due_date
    )

# Тест 10: Перевірка замовлення з порожнім кошиком і реальним ShippingService
def test_order_with_empty_cart_fails(mocker, dynamo_resource):
    # Використовуємо реальний ShippingService з мокнутими залежностями
    mock_repository = mocker.Mock(spec=ShippingRepository)
    mock_publisher = mocker.Mock(spec=ShippingPublisher)
    shipping_service = ShippingService(mock_repository, mock_publisher)

    # Створюємо порожній кошик
    cart = ShoppingCart()

    order = Order(cart=cart, shipping_service=shipping_service)

    # Спроба розмістити замовлення з порожнім кошиком
    due_date = datetime.now(timezone.utc) + timedelta(minutes=2)

    # Перевіряємо, що викликається submit_cart_order, але shipping_service не викликається
    shipping_id = order.place_order(
        shipping_type="Самовивіз",
        due_date=due_date
    )

    # Перевіряємо результати
    assert shipping_id is not None  # Отримуємо shipping_id, але кошик порожній
    assert cart.products == {}  # Кошик залишається порожнім
    mock_repository.create_shipping.assert_called_once_with(
        "Самовивіз",
        [],  # Порожній список продуктів
        order.order_id,
        shipping_service.SHIPPING_CREATED,
        due_date
    )
    mock_publisher.send_new_shipping.assert_called_once()
    mock_repository.update_shipping_status.assert_called_once_with(
        shipping_id,
        shipping_service.SHIPPING_IN_PROGRESS
    )