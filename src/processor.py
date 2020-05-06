import requests
import traceback
from wiki_dump_reader import Cleaner, iterate

from utils.wikidata import get_ner_category

class WikipediaXML2JSON_NER():
    def __init__(self, wiki_xml, lang_code):
        self.wiki_xml = wiki_xml
        self.lang_code = lang_code
        self.wikipedia_url = 'https://' + lang_code + '.wikipedia.org'
        self.wikipedia_pageprops = self.wikipedia_url + '/w/api.php?action=query&prop=pageprops&titles=%s&format=json'
        self.wiki_entities = {}
    
    def process_wiki_xml(self):
        cleaner = Cleaner()
        for title, text in iterate(self.wiki_xml):
            text = cleaner.clean_text(text)
            # TODO: Store all entities? Then do what?
            #cleaned_text, links = cleaner.build_links(text)
            
        return False
        
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
    p = WikipediaXML2JSON_NER('', 'en')
    print(p.get_qid('Machine_learning'))
    