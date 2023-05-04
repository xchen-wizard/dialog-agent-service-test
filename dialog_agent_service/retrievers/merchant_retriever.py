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
        logger.error(f"merchantSemanticSearch failed, no results:{query}")
        return None

    results = results[0:10] #TODO - use prompt stuffing strategy
    logger.info(f"Query: {query}, merchantSemanticSearch results: {results}")
            
    context = ""
    for mr in results:
        context += format_merchant_results(mr)
        context += '\n'

    return context

def format_merchant_results(mr):
    output = ""
    policy_type = mr.get("policyType")
    policy_contents = mr.get("policyContents")
    output += policy_type + "\n"
    output += policy_contents + "\n"

    return output

