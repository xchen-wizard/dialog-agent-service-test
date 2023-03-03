from pymongo import DESCENDING
from datetime import date
from dialog_agent_service.db import mongo_db
from dialog_agent_service.db import get_mysql_cnx_cursor

def get_past_k_turns(user_id: int, service_channel_id: int, k: int, endDate = date()):
  numbers = get_user_and_service_number(user_id, service_channel_id)

  messages = mongo_db['messages'].find({'userNumber': numbers['userNumber'], 'serviceNumber': numbers['serviceNumber'], 'createdAt': { '$lt': endDate}}).sort('createdAt', DESCENDING).limit(k)

  return messages

def get_user_and_service_number(user_id: int, service_channel_id):
    
  query = """
  SELECT
    pn.phoneNumber AS userNumber,
    sc.phoneNumber AS serviceNumber
  FROM phoneNumbersServiceChannels pnsc
  INNER JOIN phoneNumbers pn ON pn.id = pnsc.phoneNumberId
  INNER JOIN serviceChannels sc  ON sc.id = pnsc.serviceChannelId
  WHERE pn.userId = %s AND pn.isPrimary = 1 AND sc.id = %s
  """

  with get_mysql_cnx_cursor() as cursor:
      cursor.execute(query, (user_id, service_channel_id))
      data = cursor.fetchall()
      
  return { 'user_number': data['userNumber'], 'service_channel_number': data['serviceChannelNumber']}