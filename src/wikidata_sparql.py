import requests
import traceback
from time import sleep
import random
import threading

class WikiDataQueryHandler:
    def __init__(self, rate_limit=5):
        # Default: 5 concurrent queries. Src: stackoverflow.com/a/42590757
        self.rate_limit = rate_limit
        self.rate_limit_lock = threading.Semaphore(rate_limit)
        self.retry_after_lock = threading.Lock()
        self.SPARQL_URL = 'https://query.wikidata.org/sparql'

        self.NER_CATEGORY_MAP = [
            ['person', 'Q215627'],
            ['organization', 'Q43229'],
            ['location', 'Q17334923'],
            ['event', 'Q1656682'],
        ]
        
        self.NER_CATEGORY_QUERY = '''
            SELECT (COUNT(?item) AS ?count)
            WHERE {{
                BIND(wd:%s AS ?item).
                ?item wdt:P31*/wdt:P279* wd:%s .
            }}'''
        
        self.HTTP_REQUEST_HEADER = {'User-agent': 'IndicNLP Bot 0.3'}
        self.MAX_RETRIES = 5
        
    def send_request_critical_section(self, query):
        
        # Stall if waiting because of error 429
        if self.retry_after_lock.locked():
            self.retry_after_lock.acquire()
            self.retry_after_lock.release()
        
        try:
            self.rate_limit_lock.acquire()
            response = requests.get(self.SPARQL_URL, params={'format': 'json', 'query': query},
                                    headers=self.HTTP_REQUEST_HEADER, timeout=20)
            self.rate_limit_lock.release()
            
            # Handle too many requests error
            if response.status_code == 429 and not self.retry_after_lock.locked():
                self.retry_after_lock.acquire()
                retry_after = 30
                if 'Retry-After' in response.headers:
                    retry_after = int(response.headers["Retry-After"])+1
                elif 'Retry_After' in response.headers:
                    retry_after = int(response.headers["Retry_After"])+1
                sleep(retry_after)
                self.retry_after_lock.release()
            
            return response
        
        except requests.exceptions.Timeout:
            sleep(2*random.random())
            raise
        assert False, 'How did it reach here??'

    def get_query_result(self, query):
        for i in range(self.MAX_RETRIES):
            try:
                response = self.send_request_critical_section(query)
                
                if response.status_code == 200:
                    return response.json()
                print(response.text)
            except:
                print(traceback.format_exc())
        return {}

    def get_ner_category(self, qid):
        for category, cat_qid in self.NER_CATEGORY_MAP:
            try:
                result = self.get_query_result(self.NER_CATEGORY_QUERY % (qid, cat_qid))
                if 'results' in result and int(result['results']['bindings'][0]['count']['value']):
                    return category
            except:
                print(traceback.format_exc())
        return None
    
if __name__ == '__main__':
    sparql_handler = WikiDataQueryHandler()
    print(sparql_handler.get_ner_category('Q15646407')) # Kendriya Vidyala school
