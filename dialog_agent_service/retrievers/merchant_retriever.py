import logging
from gql import gql
from dialog_agent_service import init_gql

logger = logging.getLogger(__name__)
gql_client = init_gql()

def merchant_semantic_search(merchant_id: str, query: str):
    logger.info(f"MSS Query:{merchant_id}:{query}")
    """
    Args:
        merchant_id
        merchant_question: the merchant question
    """

    query_str = gql("""
        query MerchantSemanticSearch($merchantId: String!, $query: String!, $minSearchScore: Float, $policyTypeFilter: [String!]) {
  merchantSemanticSearch(merchantId: $merchantId, query: $query, minSearchScore: $minSearchScore, policyTypeFilter: $policyTypeFilter) {
            policyContents
            policyType
          }
        }
        """)
    vars = {
        'merchantId': merchant_id,
        'query': query,
    }
    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
      logger.error(f"Merchant Semantic Search GQL-API request failed: {err}")
      return None

    results = resp['merchantSemanticSearch']
    if not results or len(results) == 0:
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
    output += f"{policy_type}\n"
    output += f"{policy_contents}\n"
    
    return output

