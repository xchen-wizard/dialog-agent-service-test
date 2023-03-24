def index_demo_helper(es_client, dimensions: int):
    index = 'underluna-demo'

    es_client.indices.delete(index=index, ignore=[404])

    es_index_body = es_index_body = {
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
            "dims": dimensions
          }
        }
      }
    }

    es_client.indices.create(index=index, body=es_index_body)