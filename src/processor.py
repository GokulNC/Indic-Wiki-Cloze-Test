import os
import requests
import traceback
from tqdm import tqdm
from wiki_dump_reader import Cleaner, iterate

from utils.wikidata import get_ner_category
from utils.file_utils import pretty_write_json, get_valid_filename

class WikipediaXML2JSON_NER():
    def __init__(self, wiki_xml, lang_code):
        self.wiki_xml = wiki_xml
        self.lang_code = lang_code
        self.wikipedia_url = 'https://' + lang_code + '.wikipedia.org'
        self.wikipedia_pageprops = self.wikipedia_url + '/w/api.php?action=query&prop=pageprops&titles=%s&format=json'
        self.wiki_entities = {}
    
    def process_wiki_xml(self, save_to):
        os.makedirs(save_to, exist_ok=True)
        articles_path = os.path.join(save_to, 'articles')
        os.makedirs(articles_path, exist_ok=True)
        cleaner = Cleaner()
        page_titles = set()
        for title, text in tqdm(iterate(self.wiki_xml), desc='Wikipedia processing', unit=' articles'):
            # Clean each article to get plain-text and links
            text = cleaner.clean_text(text)
            cleaned_text, links = cleaner.build_links(text)
            
            # Store article as JSON
            json_path = os.path.join(articles_path, get_valid_filename(title)+'.json')
            if not os.path.isfile(json_path):
                article = {
                    'title': title,
                    'body': cleaned_text,
                    'links': links,
                    'lang_code': self.lang_code
                }
                
                pretty_write_json(article, json_path)
            
            # Save all link names in this article
            page_titles.add(title)
            for l in links:
                page_titles.add(l['link'])
        
        # Write all the page titles as txt to perform NER later
        with open(os.path.join(save_to, 'page_titles.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(page_titles)+'\n')
        
        return
        
    def perform_ner_wiki(self, page_title):
        page_title = page_title.replace(' ', '_')
        if page_title in self.wiki_entities:
            return True
        qid = self.get_qid(page_title)
        if not qid:
            return False
        self.wiki_entities[page_title] = {'QID': qid}
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
    # p = WikipediaXML2JSON_NER('', 'en')
    # print(p.get_qid('Machine_learning'))
    
    processor = WikipediaXML2JSON_NER('data/hiwiki-20200501-pages-articles-multistream.xml', 'hi')
    processor.process_wiki_xml('output/hi/')
    