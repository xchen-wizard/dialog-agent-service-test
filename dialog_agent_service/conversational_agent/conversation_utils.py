from dialog_agent_service.db import mongo_db
from dialog_agent_service.db import mysql_pool

def get_past_k_turns(user_id: str, k: int):
  messages = mongo_db['messages'].find_one({'_id': user_id})