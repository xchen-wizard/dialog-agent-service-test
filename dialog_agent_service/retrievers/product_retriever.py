import logging
from gql import gql
from dialog_agent_service import init_gql
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
gql_client = init_gql()

def product_lookup(merchant_id: str, query: str):
    """
    Args:
        merchant_id
        product_mention: the product mention
    """
    query_str = gql("""
        query ProductVariantLookup($merchantId: String!, $query: String!) {
          productVariantLookup(merchantId: $merchantId, query: $query) {
            product {
              _id
              name
              metafieldEdges {
                node {
                  namespace
                  key
                  value
                }
              }
            }
            _id
            name
            description
            listings {
              _id
              price
              inventoryCount
              subscribable
            }
          }
        }
        """)
    vars = {
        'merchantId': merchant_id,
        'query': query,
    }
    resp = gql_client.execute(document=query_str, variable_values=vars)
    results = resp['productVariantLookup']
    if not results:
        logger.error(f"productVariantLookup failed, no results:{query}")
        return None

    results = results[0:1]  #TODO: too restrictive?
    logger.info(f"Query:{query}, productVariantLookup results: {results}")

    context = ""
    for pr in results:
        context += format_product_result(pr)
        context += '\n'

    return context


def product_semantic_search(merchant_id: str, query: str):
    """
    Args:
        merchant_id
        product_question: the product question
    """

    query_str = gql("""
        query ProductVariantSemanticSearch($merchantId: String!, $query: String!, $limit: Int, $offset: Int, $minSearchScore: Float) {
          productVariantSemanticSearch(merchantId: $merchantId, query: $query, limit: $limit, offset: $offset, minSearchScore: $minSearchScore) {
            product {
              _id
              name
              metafieldEdges {
                node {
                  namespace
                  key
                  value
                }
              }
            }
            _id
            name
            description
            listings {
              _id
              price
              inventoryCount
              subscribable
            }
          }
        }
        """)
    vars = {
        'merchantId': merchant_id,
        'query': query,
    }
    resp = gql_client.execute(document=query_str, variable_values=vars)
    results = resp['productVariantSemanticSearch']
    if not results:
        logger.error(f"productVariantSemanticSearch failed, no results:{query}")
        return None

    results = results[0:10]  #TODO: prompt stuffing strategy?
    logger.info(f"Query:{query}, productVariantSemanticSearch results: {results}")

    context = ""
    for pr in results:
        context += format_product_result(pr)
        context += '\n'

    return context

def format_product_result(pr):
    BLACKLIST = ['widget']
    product = pr.get('product')
    logger.info(f"PRODUCT:{product}")
    metafields = product.get('metafieldEdges', [])
    if metafields == None:
        metafields = []
    desc = pr.get('description')
    listing = pr.get('listings')[0] #TODO - first one only for now
    price = listing.get('price')

    display_name = product.get('name') + ' - ' + pr.get('name')

    output = ""
    output += f"product name is {display_name},"
    output += f"description is {desc}"
    output += f"price is {price:.2f}"

    logger.info(f"METAFIELDS:{metafields}")
    for mf in metafields:
        node = mf['node']
        namespace = node.get('namespace')
        key = node.get('key')
        if key not in BLACKLIST:
            value = node.get('value')
            field = namespace + '.' + key
            #TODO - filter nodes by retailer whitelist
            if value and value != "":
                clean_value = parse_html(value) #TODO - temporary, data eng will do this
                output += f"{key} is {clean_value}"

    return output


def parse_html(html):
    elem = BeautifulSoup(html, 'html.parser')
    text = ''
    for e in elem.descendants:
        if isinstance(e, str):
            text += e.strip()
        elif e.name in ['br',  'p', 'h1', 'h2', 'h3', 'h4','tr', 'th']:
            text += '\n'
        elif e.name == 'li':
            text += '\n- '
    return text
