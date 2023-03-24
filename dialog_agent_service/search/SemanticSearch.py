import copy
import sys
import re
import os

from dialog_agent_service.conversational_agent.conversation_utils import get_all_faqs, get_merchant_site_ids, get_all_variants
from dialog_agent_service.app_utils import logger

from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch, helpers

class SemanticSearch():
  def __init__(self, dimensions = 768, model = 'sentence-transformers/all-mpnet-base-v2'):
    self.client = Elasticsearch(
    cloud_id=os.environ.get('ES_CLOUD_ID'),
    basic_auth=(os.environ.get('ES_USER'), os.environ.get('ES_PASSWORD'))
    )
    self.model = SentenceTransformer(model)
    self.dimensions = dimensions

  def index_faqs(self):
    site_ids = get_merchant_site_ids()

    for id in site_ids:
      site_ids[id] = site_ids[id] + '-faqs'

    self.remove_indices(site_ids)
    self.create_faq_indices(site_ids)

    faqs = get_all_faqs()

    for merchant in faqs:
      for question in merchant:
        embedding = self.model.encode(question, show_progress_bar=False)

        es_data = {
          "question": question,
          "answer": merchant[question],
          "question_vector": embedding
        }

        self.client.index(index=merchant + '-faqs', document=es_data) 

    return 'indexed faqs'


  def create_faq_indices(self, indices: dict):
    es_index_body = {
      "mappings": {
        "properties": {
          "question": {
            "type": "text"
          },
          "answer": {
            "type": "text"
          },
          "question_vector": {
            "type": "dense_vector",
            "dims": self.dimensions
          }
        }
      }
    }

    for idx in indices:
      self.client.indices.create(index=indices[idx], body=es_index_body)

  def index_products(self):
    site_ids = get_merchant_site_ids()

    for id in site_ids:
      site_ids[id] = site_ids[id] + '-products'

    self.remove_indices(site_ids)
    self.create_product_indices(site_ids)

    variants = get_all_variants()

    for id in variants:
      if variants[id]['merchant_id'] not in site_ids:
        continue

      embedding = self.model.encode(variants[id]['name'], show_progress_bar=False)
      idx = site_ids[variants[id]['merchant_id']]

      es_data = {
            "id": str(id),
            "name": variants[id]['name'],
            "name_vector": embedding
          }
      
      self.client.index(index=idx, document=es_data) 

    return 'indexed products'
  
  def create_product_indices(self, indices: dict):
    es_index_body = {
      "mappings": {
        "properties": {
          "id": {
            "type": "text"
          },
          "name": {
            "type": "text"
          },
          "name_vector": {
            "type": "dense_vector",
            "dims": self.dimensions
          }
        }
      }
    }

    for idx in indices:
      self.client.indices.create(index=indices[idx], body=es_index_body)
  
  def remove_indices(self, indices: dict):
    for idx in indices:
      self.client.indices.delete(index=indices[idx], ignore=[404])

  def faq_search(self, merchant_site_id: str, query: str):
    embedding = self.model.encode(query, show_progress_bar=False)

    sem_search = self.client.search(index=merchant_site_id + '-faqs', body={
      "query": {
        "script_score": {
          "query": {
            "match_all": {}
          },
          "script": {
            "source": "cosineSimilarity(params.queryVector, 'name_vector') + 1.0",
            "params": {
              "queryVector": embedding
            }
          }
        }
      }
    })
    
    answers = []

    for hit in sem_search['hits']['hits'][0:5]:
      answers.append(hit['_source']['answer'])

    return answers


  def product_search(self, merchant_site_id: str, query: str):
    embedding = self.model.encode(query, show_progress_bar=False)

    sem_search = self.client.search(index=merchant_site_id + '-products', body={
      "query": {
        "script_score": {
          "query": {
            "match_all": {}
          },
          "script": {
            "source": "cosineSimilarity(params.queryVector, 'name_vector') + 1.0",
            "params": {
              "queryVector": embedding
            }
          }
        }
      }
    })
    
    product_ids = []

    for hit in sem_search['hits']['hits'][0:5]:
      product_ids.append(hit['_source']['id'])

    return product_ids

  def suggest_spelling(self, term, idx):
    try:
      sem_sugg = self.client.search(index=idx, body={
            "suggest" : {
             "mytermsuggester" : {
                "text" : term,
                "term" : {
                   "field" : "name"
                 }
              }
            }
          })
    except  Exception as e:
      logger.error('error suggesting spelling')
      return None
    return sem_sugg
  
semanticSearch = SemanticSearch()