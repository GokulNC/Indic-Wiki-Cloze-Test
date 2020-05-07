import requests
import traceback
from time import sleep

SPARQL_URL = 'https://query.wikidata.org/sparql'

NER_CATEGORY_MAP = [
    ['person', 'Q215627'],
    ['organization', 'Q43229'],
    ['location', 'Q17334923'],
]

def get_query_result(query, max_retries=5):
    for i in range(max_retries):
        try:
            response = requests.get(SPARQL_URL, params = {'format': 'json', 'query': query},
                                    headers = {'User-agent': 'IndicNLP Bot 0.1'}, timeout=20)
            if response.status_code == 200:
                return response.json()
            print(response.text)
            sleep(int(response.headers["Retry-After"])) # Yes, I am from a decent family
        except:
            # print(traceback.format_exc())
            sleep(2)
        
    return {}

NER_CATEGORY_QUERY = '''
SELECT (COUNT(?item) AS ?count)
WHERE {{
    BIND(wd:%s AS ?item).
    ?item wdt:P31/wdt:P279* wd:%s .
}}
'''
def get_ner_category(qid):
    for category, cat_qid in NER_CATEGORY_MAP:
        try:
            sleep(0.5)
            result = get_query_result(NER_CATEGORY_QUERY % (qid, cat_qid))
            if 'results' in result and int(result['results']['bindings'][0]['count']['value']):
                return category
        except:
            print(traceback.format_exc())
    return None
    
if __name__ == '__main__':
    print(get_ner_category('Q15646407')) # Kendriya Vidyala school
