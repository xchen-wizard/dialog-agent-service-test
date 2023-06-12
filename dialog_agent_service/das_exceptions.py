class DASException(Exception):
    """
    This is the base class for all custom exceptions throw by DAS.
    Exceptions not inheriting from this as treated as unknown exceptions
    that we look into
    """


class LLMRequestFailed(DASException):
    """ If the request to LLM failed with some exception"""


class LLMOutputFormatIncorrect(DASException):
    """
    Sometimes we expect the LLM Output to be formatted according to some structure
    typically json. If the output if not properly formatted the subsequent parsing fails.
    """


class LLMOutputValidationFailed(DASException):
    """
    The Output from LLM failed some validation check.
    """


class RetrieverFailure(DASException):
    """
    Retriever returns empty result. Could be because of API endpoint failure
    or no relevant result.
    """


class CartGQLAPIException(DASException):
    """
    Exception for when a cart API returns an error.
    """


class CXCreatedCartException(DASException):
    """
    Exception for when a CX user already has an open cart
    """


class ProductResolutionFailure(DASException):
    """
    Resolving the product name to one in local json file failed
    """


class MultipleVariantsInCart(DASException):
    """
    We are temporarily disallowing adding multiple variants of the same
    product to cart.
    """