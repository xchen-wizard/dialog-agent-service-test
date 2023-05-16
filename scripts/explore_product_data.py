from bs4 import BeautifulSoup
import json
import tiktoken

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


def num_tokens(value, model='gpt-3.5-turbo'):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding('cl100k_base')
    if model == 'gpt-3.5-turbo':  # note: future models may deviate from this
        return len(encoding.encode(value))
    else:
        raise NotImplementedError(
            f"""num_tokens() is not presently implemented for model {model}.""",
        )


BLACKLIST = [
    'judgeme.badge', 'judgeme.widget', 'shogun.main', 'loox.reviews', 'spr.reviews', 'sanity.product_sync', 'yotpo_reviews.1000', 
    'yotpo_reviews.1001', 'okendo.ProductReviewsWidgetSnippet', 'okendo.summaryData', 'okendo.ProductListingSnippet', 
    'stamped.badge', 'stamped.reviews'
]
merchant_keys = {}
with open('product_data_20230509.jsonl', 'r') as reader:
    line = reader.readline()
    count = 0
    while line != '':
        #print(line, end='')
        line = reader.readline()
        count += 1
        try:
            rec = json.loads(line)
            # rec = rec['data']
        except:
            print(f"FAILED JSON PARSING:{line}{rec}")
        data = rec['data']
        metadata = rec['metadata']
        #print(json.dumps(rec, indent=2))
        shop = metadata['shop']
        
        metafield_edges = data.get('metafieldsEdges', [])
        for mf in metafield_edges:
            node = mf['node']
            namespace = node.get('namespace').strip('"')
            key = node.get("key").strip('"')
            node_id = f"{namespace}.{key}"
            if node_id in BLACKLIST:
                continue

            if not merchant_keys.get(shop):
                merchant_keys[shop] = {}

            if not merchant_keys[shop].get(node_id):
                merchant_keys[shop][node_id] = 0
            
            merchant_keys[shop][node_id] += 1
        
            value = node.get("value").strip('"')
            clean_value = parse_html(value)
            tokens = num_tokens(clean_value)
            print(f"MERCHANT:{shop}")
            print(f"NAMESPACE: {namespace}")
            print(f"KEY: {key}")
            print(f"VALUE: {value}")
            print(f"CLEAN VALUE: {clean_value}")
            print(f"TOKENS: {tokens}")
            if tokens > 512:
                print("TOO LARGE!")

    print(f"TOTAL RECORDS: {count}")
    print(json.dumps(merchant_keys, indent=2))