import requests
import traceback

SPARQL_URL = 'https://query.wikidata.org/sparql'

NER_CATEGORY_MAP = [
    ['person', 'Q215627'],
    ['organization', 'Q43229'],
    ['location', 'Q17334923'],
]

def get_query_result(query):
    response = requests.get(SPARQL_URL, params = {'format': 'json', 'query': query})#, timeout=10)
    return response.json()

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
            result = get_query_result(NER_CATEGORY_QUERY % (qid, cat_qid))
            if int(result['results']['bindings'][0]['count']['value']):
                return category
        except:
            print(traceback.format_exc())
    return None
    
if __name__ == '__main__':
    print(get_ner_category('Q15646407')) # Kendriya Vidyala school
