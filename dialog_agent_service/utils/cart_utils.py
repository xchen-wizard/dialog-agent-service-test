import logging
from dialog_agent_service.actions.cart_actions import cart_add_catalog_item_by_listing_id, cart_create, cart_get, cart_remove_item, cart_set_item_quantity
from dialog_agent_service.db import get_merchant
from dialog_agent_service.retrievers.product_retriever import product_lookup

logger = logging.getLogger(__name__)


def create_or_update_active_cart( merchant_id: str, user_id: int, virtual_cart: list[tuple[str, int]]):
    try:
        resolved_cart, retailer_id = resolve_product_mentions(
            merchant_id, virtual_cart)

        if virtual_cart and not resolved_cart:
            raise Exception('Could not resolve product mentions for cart')

        existing_cart = cart_get(merchant_id, user_id)

        if not existing_cart:
            existing_cart = cart_create(merchant_id, user_id, retailer_id)

        converted_cart, converted_cart_quantities, _ = active_cart_to_virtual_cart(
            existing_cart)

        cart_id = converted_cart['id']

        for listing_id in resolved_cart:
            if listing_id not in converted_cart['listings']:
                cart_add_catalog_item_by_listing_id(listing_id, cart_id)

        # resync cart so we can update quantities of newly added products
        converted_cart, converted_cart_quantities, _ = active_cart_to_virtual_cart(
            existing_cart)

        for listing_id in resolved_cart:
            if listing_id not in converted_cart['listings']:
                continue
            elif resolved_cart[listing_id]['quantity'] != converted_cart_quantities[listing_id]:
                quantity = resolved_cart[listing_id]['quantity']
                line_item_id = converted_cart['listings'][listing_id]['id']
                cart_set_item_quantity(line_item_id, cart_id, quantity)

        for listing_id in converted_cart['listings']:
            if listing_id not in resolved_cart:
                line_item_id = converted_cart['listings'][listing_id]['id']
                cart_remove_item(line_item_id, cart_id)

        return True

    except Exception as err:
        logger.error(f'update active cart failed: {err}')
        return False


def active_cart_to_virtual_cart(active_cart):
    if not active_cart:
        return {}, {}, []
    virtual_cart = {'id': active_cart['id'], 'listings': {}}
    virtual_cart_quantities = {}
    virtual_cart_list = []

    for item in active_cart['lineItems']:
        display_name = item['productName']
        if item['variantName']:
            display_name += ' - ' + item['variantName']
        virtual_cart['listings'][str(item['listingId'])] = {
            'id': item['id'],
            'freeTextName': item['freeTextName'],
            'productName': item['productName'],
            'variantName': item['variantName'],
            'currentPrice': item['currentPrice'],
            'listingId': item['listingId'],
            'quantity': item['quantity']
        }
        virtual_cart_quantities[str(item['listingId'])] = item['quantity']
        virtual_cart_list.append((display_name, item['quantity']))

    return virtual_cart, virtual_cart_quantities, virtual_cart_list


def resolve_product_mentions(merchant_id: str, virtual_cart: list[tuple[str, int]]):
    resolved_cart = {}

    for mention in virtual_cart:
        product_variants = product_lookup(merchant_id, mention[0])

        if len(product_variants) == 0:
            logger.debug(
                f'could not resolve product mentions using productLookup')
            return None

        product_variant = product_variants[0]
        product_variant['quantity'] = mention[1]
        retailer_id = product_variant['listings'][0]['retailerId']

        resolved_cart[product_variant['listings'][0]['_id']] = product_variant

    return resolved_cart, retailer_id


def sync_virtual_cart(merchant_id: str, user_id: int):
    active_cart = cart_get(merchant_id, user_id)
    if not active_cart:
        return {}
    return active_cart
