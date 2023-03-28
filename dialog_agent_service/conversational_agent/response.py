import string

newline = '\n'


def gen_non_specific_product_response(product, matches):
    return f"""
    We found multiple items that match your search for {product}. Did you mean
    {newline.join(f'{c}. {match}' for c, match in zip(string.ascii_uppercase, matches))}
    or let us know if it is something else. 
    """


def gen_variant_selection_response(product, variants):
    return f"""
    {product} is available as
    {newline.join(f'{c}. {variant} (${price})' for c, (variant, price) in zip(string.ascii_uppercase, variants.items()))} 
    Which one did you want?
    """


def gen_cart_response(cart):
    return f"""
    Your current cart has:
    {newline.join([f'- {name}  ${price} X {qty}' for name, price, qty in cart])}
    """ if cart else ""
