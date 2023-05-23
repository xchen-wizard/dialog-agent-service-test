import logging
from dialog_agent_service.actions.cart_actions import cart_add_catalog_item_by_listing_id, cart_create, cart_get, cart_remove_item, cart_set_item_quantity
from dialog_agent_service.retrievers.product_retriever import product_lookup

logger = logging.getLogger(__name__)


def create_or_update_active_cart(merchant_id: str, user_id: int, virtual_cart: list[tuple[str, int]]):
    try:
      resolved_cart = resolve_product_mentions(merchant_id, virtual_cart)

      if not resolved_cart:
          raise Exception('Could not resolve product mentions for cart')

      existing_cart = cart_get(merchant_id, user_id)

      if not existing_cart:
          existing_cart = cart_create(merchant_id, user_id)

      converted_cart, converted_cart_quantities, _ = active_cart_to_virtual_cart(existing_cart)

      cart_id = converted_cart['id']

      for listing_id in resolved_cart:
          if listing_id not in converted_cart:
              cart_add_catalog_item_by_listing_id(float(listing_id), cart_id)

              quantity = resolved_cart[listing_id]['quantity']
              cart_set_item_quantity(float(listing_id), cart_id, quantity)

          elif resolved_cart[listing_id]['quantity'] != converted_cart_quantities[listing_id]:
              quantity = resolved_cart[listing_id]['quantity']
              cart_set_item_quantity(float(listing_id), cart_id, quantity)

      for listing_id in converted_cart:
          if listing_id not in resolved_cart:
              line_item_id = converted_cart[listing_id]['id']
              cart_remove_item(line_item_id, cart_id)

      return True
          
    except Exception as err:
      logger.error(f'update active cart failed: {err}')
      return False


def active_cart_to_virtual_cart(active_cart):
    virtual_cart = {}
    virtual_cart_quantities = {}
    virtual_cart_list = []

    for item in active_cart['lineItems']:
        virtual_cart[str(item['listingId'])] = {
            'id': item['id'],
            'freeTextName': item['freeTextName'],
            'currentPrice': item['currentPrice'],
            'listingId': item['listingId'],
            'quantity': item['quantity']
        }
        virtual_cart_quantities[str(item['listingId'])] = item['quantity']
        virtual_cart_list.append(item['freeTextName'], item['quantity'])
    
    return virtual_cart, virtual_cart_quantities, virtual_cart_list

def resolve_product_mentions(merchant_id: str, virtual_cart: list[tuple[str, int]]):
    resolved_cart = {}

    for mention in virtual_cart:
        product_variants = product_lookup(merchant_id, mention[0])
        
        if len(product_variants) == 0:
            logger.debug(f'could not resolve product mentions using productLookup')
            return None
        
        product_variant = product_variants[0]
        product_variant['quantity'] = mention[1]

        resolved_cart[product_variant['listings'][0]['_id']] = product_variant
    
    return resolved_cart

def sync_virtual_cart(merchant_id: str, user_id: int):
    active_cart = cart_get(merchant_id, user_id)
    if not active_cart:
        return []
    _, _, virtual_cart_list = active_cart_to_virtual_cart(active_cart)
    return virtual_cart_list
