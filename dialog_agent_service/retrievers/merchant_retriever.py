import logging
from gql import gql
from dialog_agent_service import init_gql

logger = logging.getLogger(__name__)
gql_client = init_gql()

def merchant_semantic_search(merchant_id: str, query: str):
    """
    Args:
        merchant_id
        merchant_question: the merchant question
    """

    query_str = gql("""
        query MerchantSemanticSearch($merchantId: String!, $query: String!, $minSearchScore: Float) {
          merchantSemanticSearch(merchantId: $merchantId, query: $query, minSearchScore: $minSearchScore) {
            policyContents
            policyType
          }
        }
        """)
    vars = {
        'merchantId': merchant_id,
        'query': query,
    }
    resp = gql_client.execute(document=query_str, variable_values=vars)
    results = resp['merchantSemanticSearch']
    if not results:
        logger.warn(f"merchantSemanticSearch failed, no results:{query}")
        return None

    results = results[0:10] #TODO - use prompt stuffing strategy
    logger.debug(f"Query: {query}, merchantSemanticSearch results: {results}")
            
    context = "\n"
    for mr in results:
        context += format_merchant_results(mr)
        context += '\n'

    return context

def format_merchant_results(mr):
    output = ""
    policy_type = mr.get("policyType")
    policy_contents = mr.get("policyContents")
    output += f"policy name is {policy_type}\n"
    output += f"policy is {policy_contents}\n\n"

    return output

