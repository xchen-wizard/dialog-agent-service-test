import logging
from gql import gql
from dialog_agent_service import init_gql

logger = logging.getLogger(__name__)
gql_client = init_gql()


def create_order_summary_message(cart_id: int):
    query_str = gql('''
        mutation CreateOrderSummaryMessage($cartId: Int!) {
          createOrderSummaryMessage(cartId: $cartId) {
            content {
              body
            }
          }
        }
    ''')

    vars = {
        'cartId': cart_id
    }

    try:
        resp = gql_client.execute(document=query_str, variable_values=vars)
    except Exception as err:
        logger.exception(
            f'Create order summary message GQL-API request failed: {err}')
        return None

    order_summary = resp['createOrderSummaryMessage']
    if not order_summary:
        logger.warn(
            f'createOrderSummaryMessage failed, no results merchant_id:{cart_id}')
        return None

    logger.info(
        f'merchant_id:{cart_id}, createOrderSummaryMessage results: {order_summary}')

    return order_summary
