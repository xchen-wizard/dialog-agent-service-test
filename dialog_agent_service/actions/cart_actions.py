import logging
from dialog_agent_service.das_exceptions import CartGQLAPIException
from gql import gql
from dialog_agent_service import init_gql

logger = logging.getLogger(__name__)
gql_client = init_gql()


def cart_get(merchant_id: str, user_id: int):
    '''
      Args:
          merchant_id
          user_id

        Sample Response:
          {
            cartState: {
                id
                stage
              }
              lineItems: [..., {
                id,
                freeTextName,
                productName,
                variantName,
                currentPrice,
                listingId,
                quantity,
              }, ...]
              id,
              staffId,
              cartDiscountsTotal,
              itemsTotal,
              taxTotal,
              totalPrice,
              shippingDiscountsTotal,
              subtotal,
              shippingSavings,
            }
          }
    '''
    query_str = gql('''
      query CartGetByCustomerMerchant($merchantId: Float!, $customerId: Float!) {
        cartGetByCustomerMerchant(merchantId: $merchantId, customerId: $customerId) {
          cartState {
            id
            stage
          }
          lineItems {
            id
            freeTextName
            productName
            variantName
            currentPrice
            listingId
            quantity
          }
          id
          staffId
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
          updatedAt
        }
      }
      ''')
    vars = {
        'merchantId': float(merchant_id),
        'customerId': user_id
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(f'Get cart GQL-API request failed: {err}')
        raise CartGQLAPIException(f'Get cart GQL-API request failed') from err

    cart = resp['cartGetByCustomerMerchant']

    logger.info(
        f'merchant_id:{merchant_id}, user_id:{user_id}, CartGetByCustomerMerchant results: {cart}')

    return cart


def cart_create(merchant_id: str, user_id: int, retailer_id: str):
    '''
      Args:
          merchant_id
          user_id
          retailer_id
    '''
    query_str = gql('''
      mutation CartCreate($merchantId: Float!, $customerId: Float!, $retailerId: Float!) {
        cartCreate(merchantId: $merchantId, customerId: $customerId, retailerId: $retailerId) {
          cartState {
            id
            stage
          }
          lineItems {
            id
            freeTextName
            productName
            variantName
            currentPrice
            listingId
            quantity
          }
          id
          staffId
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
          updatedAt
        }
      }
      ''')
    vars = {
        'merchantId': int(merchant_id),
        'customerId': user_id,
        'retailerId': int(retailer_id)
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(f'Create cart GQL-API request failed: {err}')
        raise CartGQLAPIException(
            f'Create cart GQL-API request failed') from err

    cart = resp['cartCreate']

    logger.info(
        f'merchant_id:{merchant_id}, user_id:{user_id}, CartCreate results: {cart}')

    return cart


def cart_add_catalog_item_by_listing_id(listing_id: str, cart_id: float):
    '''
      Args:
          listing_id
          cart_id
    '''
    query_str = gql('''
      mutation CartAddCatalogItemByListingId($listingId: ObjectId!, $cartId: Float!) {
        cartAddCatalogItemByListingId(listingId: $listingId, cartId: $cartId) {
          cartState {
            id
            stage
          }
          lineItems {
            id
            freeTextName
            productName
            variantName
            currentPrice
            listingId
            quantity
          }
          id
          staffId
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
          updatedAt
        }
      }
      ''')
    vars = {
        'listingId': listing_id,
        'cartId': cart_id
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(f'Add listing to cart GQL-API request failed: {err}')
        raise CartGQLAPIException(
            f'Add listing to cart GQL-API request failed') from err

    cart = resp['cartAddCatalogItemByListingId']

    logger.info(
        f'listingId:{listing_id}, cartId:{cart_id}, Add listing to cart results: {cart}')

    return cart


def cart_remove_item(line_item_id: float, cart_id: float):
    '''
      Args:
          line_item_id
          cart_id
    '''
    query_str = gql('''
      mutation CartRemoveItem($lineItemId: Float!, $cartId: Float!) {
        cartRemoveItem(lineItemId: $lineItemId, cartId: $cartId) {
          cartState {
            id
            stage
          }
          lineItems {
            id
            freeTextName
            productName
            variantName
            currentPrice
            listingId
            quantity
          }
          id
          staffId
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
          updatedAt
        }
      }
      ''')
    vars = {
        'lineItemId': line_item_id,
        'cartId': cart_id
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(
            f'Remove item from cart GQL-API request failed: {err}')
        raise CartGQLAPIException(
            f'Remove item from cart GQL-API request failed') from err

    cart = resp['cartRemoveItem']

    logger.info(
        f'lineItemId:{line_item_id}, cartId:{cart_id}, Remove item from cart results: {cart}')

    return cart


def cart_set_item_quantity(line_item_id: float, cart_id: float, quantity: float):
    '''
      Args:
          line_item_id
          cart_id
    '''
    query_str = gql('''
      mutation CartSetItemQuantity($quantity: Float!, $lineItemId: Float!, $cartId: Float!) {
        cartSetItemQuantity(quantity: $quantity, lineItemId: $lineItemId, cartId: $cartId) {
          cartState {
            id
            stage
          }
          lineItems {
            id
            freeTextName
            productName
            variantName
            currentPrice
            listingId
            quantity
          }
          id
          staffId
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
          updatedAt
        }
      }
      ''')
    vars = {
        'lineItemId': line_item_id,
        'cartId': cart_id,
        'quantity': quantity
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(
            f'Set cart item quantity GQL-API request failed: {err}')
        raise CartGQLAPIException(
            f'Set cart item quantity GQL-API request failed') from err

    cart = resp['cartSetItemQuantity']

    logger.info(
        f'lineItemId:{line_item_id}, cartId:{cart_id}, Set cart item quantity results: {cart}')

    return cart


def cart_go_to_review_order(cart_id: float):
    '''
      Args:
          cart_id
    '''
    query_str = gql('''
      mutation cartGoToReviewOrder($cartId: Float!) {
        cartGoToReviewOrder(cartId: $cartId) {
          cartState {
            id
            stage
          }
          lineItems {
            id
            freeTextName
            productName
            variantName
            currentPrice
            listingId
            quantity
          }
          id
          staffId
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
          updatedAt
        }
      }
      ''')
    vars = {
        'cartId': cart_id
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(
            f'Cart go to review order GQL-API request failed: {err}')
        raise CartGQLAPIException(
            f'Cart go to review order GQL-API request failed') from err

    cart = resp['cartGoToReviewOrder']

    logger.info(
        f'Set state review order for cartId:{cart_id}')

    return cart


def cart_delete(cart_id: float):
    '''
      Args:
          cart_id
    '''
    query_str = gql('''
      mutation cartDelete($cartId: Float!) {
        cartDelete(cartId: $cartId) {
          cartState {
            id
            stage
          }
          lineItems {
            id
            freeTextName
            productName
            variantName
            currentPrice
            listingId
            quantity
          }
          id
          staffId
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
          updatedAt
        }
      }
      ''')
    vars = {
        'cartId': cart_id
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.error(f'Cart delete GQL-API request failed: {err}')
        raise CartGQLAPIException(
            f'Cart delete GQL-API request failed') from err

    cart = resp['cartDelete']

    logger.info(
        f'Delete cart with cartId:{cart_id}')

    return cart
