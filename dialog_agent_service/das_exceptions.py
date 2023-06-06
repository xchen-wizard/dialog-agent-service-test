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


class T5CartOutputFailure(DASException):
    """
    We predict cart using T5 first to fetch a shortlist of products.
    If that prediction fails or the output is not formatted correctly,
    we throw this exception
    """


class CartGQLAPIException(Exception):
    """
    Exception for when a cart API returns an error.
    """
