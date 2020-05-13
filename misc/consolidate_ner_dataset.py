import os, sys
import json
import requests
import traceback
from glob import glob
from tqdm import tqdm

from utils.file_utils import pretty_write_json

class Wiki_NER_Consolidator:
    def __init__(self, lang_code, ner_file, wiki_articles_dir):
        self.lang_code = lang_code
        # Args = (qid)
        self.WIKIDATA_ALIASES_API = 'https://www.wikidata.org/w/api.php?action=wbgetentities&ids=%s&props=aliases&format=json&languages=' + lang_code
        
        with open(ner_file, encoding='utf-8') as f:
            self.ner_data = json.load(f)
        
        self.scrape_wiki_entities(wiki_articles_dir)
        self.ner_to_qmap()
        
    def scrape_wiki_entities(self, wiki_articles_dir):
        print('Scraping for aliases from Wikipedia articles...')
        articles_json = sorted(glob(os.path.join(wiki_articles_dir, '*.json')))
        for article_file in tqdm(articles_json, desc='Processing', unit=' articles'):
            try:
                with open(article_file, encoding='utf-8') as f:
                    article = json.load(f)
            except:
                print(traceback.format_exc())
                print('Unable to parse:', article_file)
                continue
            # TODO: Do more aggressive scraping rather than just links. Think of a logic
            for entity in article['links']:
                link_name = entity['link'].replace(' ', '_')
                if link_name in self.ner_data:
                    if 'aliases' in self.ner_data[link_name]:
                        self.ner_data[link_name]['aliases'].add(entity['text'])
                    else:
                        self.ner_data[link_name]['aliases'] = set([entity['text']])
        
        return
    
    def ner_to_qmap(self):
        self.qid2ner = {}
        for entity, data in tqdm(self.ner_data.items(), desc='Deduplicating NER data...', unit=' entities'):
            if 'QID' in data and 'NER_Category' in data:
                qid = data['QID']
                entities = set([entity.replace('_', ' ')])
                if 'aliases' in data:
                    entities.update(data['aliases'])
                if qid in self.qid2ner:
                    self.qid2ner[qid]['entities'].update(entities)
                    if self.qid2ner[qid]['tag'] != data['NER_Category']:
                        print('Ambiguous tag for QID:', qid)
                else:
                    self.qid2ner[qid] = {
                        'tag': data['NER_Category'],
                        'entities': entities
                    }
        print('We have a total of %d QIDs,' % len(self.qid2ner))
        num_entities = 0
        for qid, data in self.qid2ner.items():
            num_entities += len(data['entities'])
        print('And a total of %d unique entities' % num_entities)
        return
    
    def get_wikidata_aliases(self, qid):
        try:
            response = requests.get(self.WIKIDATA_ALIASES_API % qid)
            #if response.status_code != 200:
            #    return None
            data = response.json()
            #if not 'entities' in data or 'aliases' not in data['entities'][qid]:
            #    return None
            aliases = data['entities'][qid]['aliases']
            if self.lang_code not in aliases:
                return set()
            aliases = aliases[self.lang_code]
            aliases = set(a['value'] for a in aliases)
            return aliases
        except:
            print(traceback.format_exc())
        return None
    
    def consolidate(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        dataset_file = os.path.join(output_dir, 'ner_dataset.json')
        total_entities = 0
        for qid in tqdm(self.qid2ner, desc='Quering WikiData for aliases', unit=' QIDs'):
            aliases = self.get_wikidata_aliases(qid)
            if aliases:
                self.qid2ner[qid]['entities'].update(aliases)
            # Convert set to list since set is not serializable
            self.qid2ner[qid]['entities'] = list(self.qid2ner[qid]['entities'])
            total_entities += len(self.qid2ner[qid]['entities'])
        
        print('We now have a NER dataset of %d QIDs and %d entities!' % (len(self.qid2ner), total_entities))
        # TODO: Any better format to save?
        print('Writing final dataset to:', dataset_file)
        pretty_write_json(self.qid2ner, dataset_file)
        return

if __name__ == '__main__':
    lang_code, ner_file, articles_folder, output_folder = sys.argv[1:]
    consolidator = Wiki_NER_Consolidator(lang_code, ner_file, articles_folder)
    # print(consolidator.get_wikidata_aliases('Q1001')) # Test Gandhi's aliases
    consolidator.consolidate(output_folder)
