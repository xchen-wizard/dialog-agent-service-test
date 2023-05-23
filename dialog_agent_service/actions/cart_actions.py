import logging
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
              stage
            }
            lineItems: [..., {
              id,
              freeTextName,
              currentPrice,
              listingId,
              quantity,
            }, ...]
            id,
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
            stage
          }
          lineItems {
            id
            freeTextName
            currentPrice
            listingId
            quantity
          }
          id
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
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
      logger.error(f'Get cart GQL-API request failed: {err}')
      return None
  
  cart = resp['cartGetByCustomerMerchant']
  if not cart:
      logger.warn(f'CartGetByCustomerMerchant failed, no results merchant_id:{merchant_id}, user_id:{user_id}')
      return None
  
  logger.info(f'merchant_id:{merchant_id}, user_id:{user_id}, CartGetByCustomerMerchant results: {cart}')

  return cart


def cart_create(merchant_id: str, user_id: int):
  '''
    Args:
        merchant_id
        user_id
  '''
  query_str = gql('''
      mutation CartCreate($merchantId: Float!, $customerId: Float!) {
        cartCreate(merchantId: $merchantId, customerId: $customerId) {
          cartState {
            stage
          }
          lineItems {
            id
            freeTextName
            currentPrice
            listingId
            quantity
          }
          id
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
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
      logger.error(f'Create cart GQL-API request failed: {err}')
      return None
  
  cart = resp['cartCreate']
  if not cart:
      logger.warn(f'CartCreate failed, no results merchant_id:{merchant_id}, user_id:{user_id}')
      return None
  
  logger.info(f'merchant_id:{merchant_id}, user_id:{user_id}, CartCreate results: {cart}')

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
            stage
          }
          lineItems {
            id
            freeTextName
            currentPrice
            listingId
            quantity
          }
          id
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
        }
      }
      ''')
  vars = {
      'listingId': float(listing_id),
      'cartId': cart_id
  }

  try:
    resp = gql_client.execute(document=query_str, variable_values=vars)
  except Exception as err:
      logger.error(f'Add listing to cart GQL-API request failed: {err}')
      return None
  
  cart = resp['cartAddCatalogItemByListingId']
  if not cart:
      logger.warn(f'Add listing to cart failed, no results listingId:{listing_id}, cartId:{cart_id}')
      return None
  
  logger.info(f'listingId:{listing_id}, cartId:{cart_id}, Add listing to cart results: {cart}')

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
            stage
          }
          lineItems {
            id
            freeTextName
            currentPrice
            listingId
            quantity
          }
          id
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
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
      logger.error(f'Remove item from cart GQL-API request failed: {err}')
      return None
  
  cart = resp['cartRemoveItem']
  if not cart:
      logger.warn(f'Remove item from cart failed, no results lineItemId:{line_item_id}, cartId:{cart_id}')
      return None
  
  logger.info(f'lineItemId:{line_item_id}, cartId:{cart_id}, Remove item from cart results: {cart}')

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
            stage
          }
          lineItems {
            id
            freeTextName
            currentPrice
            listingId
            quantity
          }
          id
          cartDiscountsTotal
          itemsTotal
          taxTotal
          totalPrice
          shippingDiscountsTotal
          subtotal
          shippingSavings
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
      logger.error(f'Set cart item quantity GQL-API request failed: {err}')
      return None
  
  cart = resp['cartSetItemQuantity']
  if not cart:
      logger.warn(f'Set cart item quantity failed, no results lineItemId:{line_item_id}, cartId:{cart_id}')
      return None
  
  logger.info(f'lineItemId:{line_item_id}, cartId:{cart_id}, Set cart item quantity results: {cart}')

  return cart
