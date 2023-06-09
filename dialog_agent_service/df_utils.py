from __future__ import annotations

import logging
import os

from google.cloud import dialogflow_v2
from google.cloud.dialogflow_v2.types import Context
from google.cloud.dialogflow_v2.types import QueryInput
from google.cloud.dialogflow_v2.types import QueryParameters
from google.cloud.dialogflow_v2.types import TextInput
from google.protobuf.json_format import MessageToDict

from dialog_agent_service.data_types import DASResponse
from dialog_agent_service.data_types import TemplateMessage

logger = logging.getLogger()

MAX_TRIES = 3  # max num of tries for df detect_intent calls
DF_INF_CHAR_LIMIT = 256  # DF char limit at inference time


async def get_df_response(req: dict, user_contexts: dict):
    client = dialogflow_v2.SessionsAsyncClient()
    # Initialize request argument(s)
    text = str(req.get('text'))
    if len(text) > DF_INF_CHAR_LIMIT:
        logger.warning(
            f'Truncate query text due to DF char limit. Original message:\n{text}',
        )
        text = text[:DF_INF_CHAR_LIMIT]

    request = dialogflow_v2.DetectIntentRequest(
        session=user_contexts.get('sessionStr'),
        query_params=QueryParameters(
            contexts=[Context(c) for c in user_contexts.get('contexts')],
        ),
        query_input=QueryInput(
            text=TextInput(
                text=text,
                language_code=os.getenv('LANGUAGE', 'en-US'),
            ),
        ),
    )
    logger.debug(f'df request:\n{request}')

    for _ in range(MAX_TRIES):
        try:
            response = await client.detect_intent(request=request)
            logger.debug(f'df response:\n{response}')
            if 'webhook_status' in response:  # if a webhook call was involved
                if response.webhook_status.code == 0:
                    return MessageToDict(response._pb, preserving_proto_field_name=True)
                elif response.webhook_status.code == 4:
                    logger.exception(
                        'DF webhook error:\n{response.webhook_status.message}',
                    )
                    return {
                        'query_result': {
                            'fulfillment_text': 'no response',
                            'webhook_payload': {'autoResponse': False},
                        },
                    }
                # else: retry for other webhook errors
            elif response.query_result.intent.display_name == 'Default Welcome Intent':  # welcome intent
                return MessageToDict(response._pb, preserving_proto_field_name=True)
            else:  # not welcome intent and response does not contain webhook status
                logger.exception(
                    'DF response does not contain webhook status! Retrying...',
                )
        except Exception as e:
            logger.exception(f'Call to DF resulted in failure:\n{e}')
    return None


def parse_df_response(df_response: dict | None, vendor_id: str) -> dict:
    if not df_response:
        response = DASResponse(
            vendorId=vendor_id,
            templateMessages=[
                TemplateMessage(
                    templateTypeId='autoresponder',
                )._asdict(),
            ],
            autoResponse=False,
            message='template',
        )._asdict()
    else:  # df_response is a dict
        response = DASResponse(
            vendorId=vendor_id,
            templateMessages=[
                TemplateMessage(
                    **tm,
                )._asdict() for tm in df_response['query_result']['webhook_payload'].get('templateMessages', [])
            ],
            autoResponse=df_response['query_result']['webhook_payload'].get(
                'autoResponse', True,
            ),
            message=df_response['query_result']['fulfillment_text'],
        )._asdict()
    logger.debug(f'DASResponse: {response}')
    return response
