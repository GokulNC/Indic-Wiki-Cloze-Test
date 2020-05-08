'''
Code to run WikiData Queries for NER.

Note: WikiData's hosted SPARQL service has a rate-limit of 5 concurrent queries per IP.
Ensur you comply with that to avoid error 429. Src: stackoverflow.com/a/42590757
'''

import requests
import traceback
from time import sleep
import random
import threading

class WikiDataQueryHandler:
    def __init__(self, rate_limit=5):
        self.rate_limit = rate_limit
        self.rate_limit_lock = threading.Semaphore(rate_limit)
        self.retry_after_lock = threading.Lock()
        self.SPARQL_URL = 'https://query.wikidata.org/sparql'
        
        # Get a property of an entity. Args: (qid, pid)
        self.WIKIDATA_GET_CLAIM_API = 'https://www.wikidata.org/w/api.php?action=wbgetclaims&entity=%s&property=%s&props=&format=json'
        
        self.ENTITIY2QID = {
            'human': 'Q5',
            'person': 'Q215627',
            'organization': 'Q43229',
            'location': 'Q17334923',
            'event': 'Q1656682',
        }

        self.NER_CATEGORY_MAP = [
            # ['person', 'PER'],
            ['organization', 'ORG'],
            ['location', 'LOC'],
            ['event', 'EVE'],
        ]
        
        # Returns 1 if the given entity belongs to the given category
        # Args: (entity_qid, category_qid)
        self.NER_CATEGORY_QUERY = '''
            SELECT (COUNT(?item) AS ?count)
            WHERE {{
                BIND(wd:%s AS ?item).
                ?item wdt:P31*/wdt:P279* wd:%s .
            }}'''
        
        self.HTTP_REQUEST_HEADER = {'User-agent': 'IndicNLP Bot 0.4'}
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
        # Run the given query on SPARQL
        for i in range(self.MAX_RETRIES):
            try:
                response = self.send_request_critical_section(query)
                
                if response.status_code == 200:
                    return response.json()
                print(response.text)
            except:
                print(traceback.format_exc())
        return {}
    
    def check_if_direct_instance_of(self, qid, target_qid):
        # Check if entity `qid` is an instance of `target_qid`
        try: # Property P31 means `instance of`
            response = requests.get(self.WIKIDATA_GET_CLAIM_API % (qid, 'P31'))
            if target_qid == response.json()['claims']['P31'][0]['mainsnak']['datavalue']['value']['id']:
                return True
        except:
            pass #print(traceback.format_exc())
        return False

    def get_ner_category(self, qid):
        
        # Check if human directly using WikiData API
        if self.check_if_direct_instance_of(qid, self.ENTITIY2QID['human']):
            return 'PER' # Person
        
        # Run SPARQL for other categories
        for category, tag in self.NER_CATEGORY_MAP:
            cat_qid = self.ENTITIY2QID[category]
            try:
                result = self.get_query_result(self.NER_CATEGORY_QUERY % (qid, cat_qid))
                if 'results' in result and int(result['results']['bindings'][0]['count']['value']):
                    return tag # Return the entity category if 1
            except:
                print(traceback.format_exc())
        return None


if __name__ == '__main__':
    sparql_handler = WikiDataQueryHandler()
    print(sparql_handler.get_ner_category('Q15646407')) # Ensure Kendriya Vidyala school is an organization
    print(sparql_handler.check_if_direct_instance_of('Q1001', 'Q5')) # Ensure Mahatma Gandhi is a human
