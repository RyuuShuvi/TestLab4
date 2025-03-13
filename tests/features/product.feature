Feature:product
  We want to test that product functionality works correctly

  Scenario: Create a product with negative available amount
    When I create product with availability "-123", name "any" and price "123"
    Then Failure to create a product

  Scenario: Create a product with negative price
    When I create product with availability "123", name "any" and price "-123"
    Then Failure to create a product

  Scenario: Create a product with a name less than 3
    When I create product with availability "123", name "an" and price "123"
    Then Failure to create a product

  Scenario: Create a product with the price written in words.
    When I create product with availability "123", name "any" and price "one"
    Then Failure to create a product

  Scenario: Create a product with None price.
    When I create product with availability "123", name "any" and None price
    Then Failure to create a product

  Scenario: Check the product for availability
    Given The product has availability of "123"
    When I check the product availability amount for "124"
    Then The product is not available in the specified quantity

  Scenario: Successful buy a product
    Given The product has availability of "123"
    When I buy "3" items
    Then The product availability has to be "120"

  Scenario: Verify if entered name equals
    Given The product has name of "123"
    And The second product has name of "123"
    When I check the product name for the second product name
    Then The product equals with other product