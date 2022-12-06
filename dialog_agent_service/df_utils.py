from __future__ import annotations

import os
from google.cloud import dialogflow_v2
from google.cloud.dialogflow_v2.types import (QueryInput, TextInput, QueryParameters, Context)
from google.protobuf.json_format import MessageToDict
from dialog_agent_service.data_types import TemplateMessage, DASResponse

import logging

logger = logging.getLogger()

MAX_TRIES = 3


async def get_df_response(req: dict, user_contexts: dict):
    client = dialogflow_v2.SessionsAsyncClient()
    # Initialize request argument(s)
    request = dialogflow_v2.DetectIntentRequest(
        session=user_contexts.get('sessionStr'),
        query_params=QueryParameters(contexts=[Context(c) for c in user_contexts.get('contexts')]),
        query_input=QueryInput(text=TextInput(
            text=req.get('text'),
            language_code=os.getenv('LANGUAGE', 'en-US')
        ))
    )
    logger.debug(f'df request: {request}')

    for _ in range(MAX_TRIES):
        try:
            response = await client.detect_intent(request=request)
            if 'webhook_status' in response:  # if a webhook call was involved
                if response.webhook_status.code == 0:
                    return MessageToDict(response._pb)
                elif response.webhook_status.code == 4:
                    logger.error('DF webhook error:\n{response.webhook_status.message}')
                    return {'queryResult': {
                              'fulfillmentText': 'no response',
                              'webhookPayload': {'autoResponse': False}
                    }}
                # else: retry for other webhook errors
            elif response.query_result.intent.display_name == 'Default Welcome Intent':  # welcome intent
                return MessageToDict(response._pb)
            else:  # not welcome intent and response does not contain webhook status
                logger.error("DF response does not contain webhook status! Retrying...")
        except Exception as e:
            logger.error(f"Call to DF resulted in failure:\n{e}")
    return None


def parse_df_response(df_response: dict | None, vendor_id) -> dict:
    if not df_response:
        return DASResponse(
            vendorId=vendor_id,
            templateMessages=[TemplateMessage(
                templateTypeId='autoresponder'
            )],
            autoResponse=False
        ).__as_dict()
    else:
        df_response['queryResult']['webhookPayload']
    pass