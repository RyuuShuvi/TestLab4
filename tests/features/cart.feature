Feature:Shopping cart
  We want to test that shopping cart functionality works correctly

  Scenario: Successful add product to cart
    Given The product has availability of "123"
    And An empty shopping cart
    When I add product to the cart in amount "123"
    Then Product is added to the cart successfully

  Scenario: Failed add product to cart
    Given The product has availability of "123"
    And An empty shopping cart
    When I add product to the cart in amount "124"
    Then Product is not added to cart successfully

  Scenario: Calculating total price
    Given The product has price of "100"
    And An empty shopping cart
    When I add product to the cart in amount "5"
    Then The total price has to be "500"

  Scenario: Remove product from cart
    Given The product has price of "100"
    And An empty shopping cart
    When I add product to the cart in amount "5"
    And I remove product form cart
    Then Product is removed from cart successfully

  Scenario: Find product in cart
    Given The product has price of "100"
    And An empty shopping cart
    When I add product to the cart in amount "5"
    And I find the product in the cart
    Then The found product is the same as the added product