import string
from textwrap import dedent
import logging
logger = logging.getLogger(__name__)

newline = '\n'


def gen_non_specific_product_response(matches):
    if matches:
        return f"""
We have several products that may be what you’re looking for.

{newline.join(f'{c}. {match}' for c, match in zip(string.ascii_uppercase, matches))}

Do any of these sound right, or are you looking for something different?
"""


def gen_variant_selection_response(product, variants):
    return f"""
Sure thing! The {product} is available in the following variations.

{newline.join(f'{c}. {variant} (${price})' for c, (variant, price) in zip(string.ascii_uppercase, variants.items()))}

Which would you like to add to your order?
"""


def gen_cart_response(cart, prices):
    if not cart:
        return "Is there anything else we can help you find today?"
    cart_display = "Your cart is empty"
    if cart:
        cart_display = "Your current cart has:"
        for (name, qty), price in zip(cart, prices):
            cart_display += f"\n- {name}: ${price} x {qty}"
    cta = "Would you like to keep shopping, or are you ready to check out?"
    return cart_display + "\n" + cta


def gen_opening_response():
    return """
I’d be happy to place an order for you! What would you like to add to your cart?
"""