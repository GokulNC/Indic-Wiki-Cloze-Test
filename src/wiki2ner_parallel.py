'''
To find the NER categories of all the Wikipedia page titles (from a txt file) using WikiData.

USAGE:
$ <script.py> <lang_code> <txt_file> <output_folder>

EXAMPLE:
$ python wiki2ner_parallel.py hi output/hi/page_titles.txt output/hi/
'''

import os, sys
import requests
import traceback
from threading import Thread
from time import sleep

from utils.wikidata import get_ner_category
from utils.file_utils import pretty_write_json

class WikiNER_Downloader():
    def __init__(self, lang_code):
        self.lang_code = lang_code
        self.wikipedia_url = 'https://' + lang_code + '.wikipedia.org'
        self.wikipedia_pageprops = self.wikipedia_url + '/w/api.php?action=query&titles=%s&redirects&prop=redirects&prop=pageprops&format=json'
    
    def process_titles_parallel(self, txt_file, save_to, num_workers=8):
        # Read list of all page titles
        with open(txt_file, encoding='utf-8') as f:
            titles = f.read().split('\n')
        
        # Prepare variables for the workers
        results = [{} for i in range(num_workers)]
        titles_per_thread = (len(titles)+num_workers) // num_workers
        threads = []
        self.threads_counter = [0 for i in range(num_workers)]
        
        # Start all worker threads
        for t_id in range(num_workers):
            t = Thread(target=self.ner_wiki_worker,
                       args=(t_id, titles[t_id*titles_per_thread : (t_id+1)*titles_per_thread], results[t_id]))
            t.start()
            threads.append(t)
            sleep(0.5) # Avoid hitting hard in the beginning
        
        # Start the status printing thread
        self.print_worker_status = True
        printer_thread = Thread(target=self.worker_status_printer, args=(num_workers,))
        printer_thread.start()
        
        # Wait till all threads are complete
        for t_id in range(num_workers):
            threads[t_id].join()
        
        self.print_worker_status = False
        
        ner_data = {}
        for t_id in range(num_workers):
            ner_data.update(results[t_id])
        
        print('Workers completed the work. Saving...')
        
        os.makedirs(save_to, exist_ok=True)
        ner_file = os.path.join(save_to, 'ner_list.json')
        pretty_write_json(ner_data, ner_file)
        return
    
    def worker_status_printer(self, num_workers):
        while self.print_worker_status:
            # print('\n\n%5s\t%s' % ('T_ID', 'COUNTER'))
            # for t_id in range(num_workers):
            #     print('%5d\t%d' % (t_id, self.threads_counter[t_id]))
            print('TOTAL PROCESSED -->', sum(self.threads_counter))
            sleep(1*60)
        return
        
    def ner_wiki_worker(self, t_id, titles, wiki_entities):
        for title in titles:
            self.fetch_ner_wiki(title, wiki_entities)
            self.threads_counter[t_id] += 1
        return
        
    def fetch_ner_wiki(self, page_title, wiki_entities):
        page_title = page_title.replace(' ', '_')
        
        # Find WikiData QID for the Wikipedia Article
        qid = self.get_qid(page_title)
        wiki_entities[page_title] = {'QID': qid}
        if not qid:
            return False
        
        # Find NER category for that entity from WikiData using QID
        ner_category = get_ner_category(qid)
        if not ner_category:
            return False
        wiki_entities[page_title]['NER_Category'] = ner_category
        return True
    
    def get_qid(self, page_title):
        try:
            response = requests.get(self.wikipedia_pageprops % page_title, timeout=5)
            pages = response.json()['query']['pages']
            qids = []
            for page in pages:
                if 'pageprops' in pages[page]:
                    qids.append(pages[page]['pageprops']['wikibase_item'])
            
            return qids[0] if qids else None
        except:
            # print(traceback.format_exc())
            print('Wikipedia Query for %s failed' % page_title)
            return None
        
if __name__ == '__main__':
    lang_code, txt_file, output_folder = sys.argv[1:]
    processor = WikiNER_Downloader(lang_code)
    processor.process_titles_parallel(txt_file, output_folder)
