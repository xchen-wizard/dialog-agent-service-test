import logging
from gql import gql
from dialog_agent_service import init_gql

logger = logging.getLogger(__name__)
gql_client = init_gql()


def product_lookup(merchant_id: str, query: str, limit=25):
    """
    Args:
        merchant_id
        product_mention: the product mention
        limit: how many variants to return
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
              retailerId
            }
          }
        }
        """)
    vars = {
        'merchantId': merchant_id,
        'query': query,
        'limit': limit
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(f"Product Lookup GQL-API request failed: {err}")
        return None

    results = resp['productVariantLookup']
    if not results or len(results) == 0:
        logger.warn(f"productVariantLookup failed, no results:{query}")
        return None

    results = results[0:10]
    logger.info(f"Query:{query}, productVariantLookup results: {results}")

    return results


def product_variants_to_context(product_variants: list):
    """
    Args:
        product_variants: list of product_variants that are returned from product_lookup or product_semantic_search
    """
    context = ""
    if not product_variants:
        return context
    for pr in product_variants:
        context += format_product_result(pr)
        context += '\n'

    return context


def product_semantic_search(merchant_id: str, query: str):
    logger.info(f"PSS Query: {merchant_id}:{query}")

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
        'minSearchScore': 0,
        'limit': 10
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(
            f"Product Semantic Search GQL-API request failed: {err}")
        return None

    results = resp['productVariantSemanticSearch']
    if not results or len(results) == 0:
        logger.warn(f"productVariantSemanticSearch failed, no results:{query}")
        return None

    results = results[0:10]  # TODO: prompt stuffing strategy?
    logger.debug(
        f"Query:{query}, productVariantSemanticSearch results: {results}")

    context = "\n\n"
    for pr in results:
        context += format_product_result(pr, include_metafields=False)
        context += '\n'

    return context


def format_product_result(pr, include_metafields=True):
    BLACKLIST = [
        'subscriptions.subscription_id',
        'subscriptions.original_to_hidden_variant_map',
        'mc-facebook.google_product_category',
        'img.images', 'img.image_2'
    ]
    output = ""

    product = pr.get('product')
    display_name = product.get('name') + ' - ' + pr.get('name')
    output += f"\n{display_name}: "

    desc = pr.get('description')
    if desc:
        output += f"{desc}"

    listing = pr.get('listings')[0]  # TODO - first one only for now
    price = listing.get('price')
    if price:
        output += f" price is ${price:.2f}."

    if include_metafields:
        metafields = product.get('metafieldEdges', [])
        if metafields:
            for mf in metafields:
                node = mf['node']
                namespace = node.get('namespace').strip('"')
                key = node.get('key').strip('"')
                field = namespace + '.' + key
                if field not in BLACKLIST:
                    value = node.get('value')

                    # TODO - filter nodes by retailer whitelist
                    if value and value != "":
                        # TODO - temporary, data eng will do this
                        clean_value = value.strip('"').replace('\n', ' ')
                        output += f" {field} is {clean_value}."

    return output
