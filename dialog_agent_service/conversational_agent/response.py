import string
from textwrap import dedent
import logging
logger = logging.getLogger(__name__)

newline = '\n'

def gen_non_specific_product_response(product, matches):
    if matches:
        return f"""
        We found multiple items that match your search for {product}. Did you mean
        {newline.join(f'{c}. {match}' for c, match in zip(string.ascii_uppercase, matches))}
        or let us know if it is something else. 
        """
    else:
        # TODO: eventually we will just change the task to recommendation and let chatgpt respond
        return f"""
        We couldn't narrow down your search for {product}. Would you like some recommendations.
        """


def gen_variant_selection_response(product, variants):
    return f"""
    {product} is available as
    {newline.join(f'{c}. {variant} (${price})' for c, (variant, price) in zip(string.ascii_uppercase, variants.items()))}
    Which one did you want?
    """


def gen_cart_response(cart):
    cart_display = ""
    if cart:
        cart_display = dedent(f"""
            Your current cart has:\n{newline.join([f'- {name}: ${price} x {qty}' for name, price, qty in cart])}
        """).strip("\n")
    return cart_display


def gen_opening_response():
    return """
    Are there any particular products you are interested in? We can also help you select one if you are unsure. Let us know
    """