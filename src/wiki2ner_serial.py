'''
To find the NER categories of all the Wikipedia page titles (from a txt file) using WikiData.

USAGE:
$ <script.py> <lang_code> <txt_file> <output_folder>

EXAMPLE:
$ python wiki2ner_serial.py hi output/hi/page_titles.txt output/hi/
'''

import os, sys
import requests
import traceback
from tqdm import tqdm

from utils.wikidata import get_ner_category
from utils.file_utils import pretty_write_json

class WikiNER_DownloaderSerial():
    def __init__(self, lang_code):
        self.lang_code = lang_code
        self.wikipedia_url = 'https://' + lang_code + '.wikipedia.org'
        self.wikipedia_pageprops = self.wikipedia_url + '/w/api.php?action=query&prop=pageprops&titles=%s&format=json'
        self.wiki_entities = {}
    
    def process_titles_serial(self, txt_file, save_to):
        # Read list of all page titles
        with open(txt_file, encoding='utf-8') as f:
            titles = f.read().split('\n')
        
        for title in tqdm(titles, desc='Performing NER from WikiData', unit=' entities'):
            self.fetch_ner_wiki(title)
        
        ner_file = os.path.join(save_to, 'ner_list.json')
        pretty_write_json(self.wiki_entities, ner_file)
        
    def fetch_ner_wiki(self, page_title):
        page_title = page_title.replace(' ', '_')
        if page_title in self.wiki_entities:
            return True
        
        # Find WikiData QID for the Wikipedia Article
        qid = self.get_qid(page_title)
        self.wiki_entities[page_title] = {'QID': qid}
        if not qid:
            return False
        
        # Find NER category for that entity from WikiData using QID
        ner_category = get_ner_category(qid)
        if not ner_category:
            return False
        self.wiki_entities[page_title]['NER_Category'] = ner_category
        return True
    
    def get_qid(self, page_title):
        try:
            # if page_title in self.wiki_entities:
            #     return self.wiki_entities[page_title]['QID']
            response = requests.get(self.wikipedia_pageprops % page_title, timeout=5)
            pages = response.json()['query']['pages']
            qids = []
            for page in pages:
                if 'pageprops' in pages[page]:
                    qids.append(pages[page]['pageprops']['wikibase_item'])
            
            return qids[0] if qids else None
        except:
            print(traceback.format_exc())
            return None
        
if __name__ == '__main__':
    lang_code, txt_file, output_folder = sys.argv[1:]
    processor = WikiNER_DownloaderSerial(lang_code)
    processor.process_titles_serial(txt_file, output_folder)
