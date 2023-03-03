from enum import Enum

class Response(Enum):
  SUGGESTION = 'suggestion'

def conversation_response(merchant_id: str, user_id: int, service_channel_id: str):
  return { 'response': 'my response', 'responseType': Response('suggestion')}

