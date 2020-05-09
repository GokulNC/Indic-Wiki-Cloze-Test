'''
Code to generate cloze task dataset given the list of all Wiki articles and Entity-to-category NER map.

USAGE:
$ <script.py> <lang_code> <ner_file> <articles_folder> <output_folder>

EXAMPLE:
$ python src/generate_cloze.py hi output/hi/ner_list.json output/hi/articles/ output/hi/
'''

import os, sys
import json
from glob import glob
from tqdm import tqdm

from utils.lang_utils import EOS_DELIMITERS
from utils.file_utils import pretty_write_json, get_verified_path

class ClozeGenerator():
    def __init__(self, lang_code, wiki_articles_dir, ner_file):
        self.lang_code = lang_code
        self.full_stop = EOS_DELIMITERS[lang_code]
        
        self.articles_dir = wiki_articles_dir
        self.articles_json = sorted(glob(os.path.join(wiki_articles_dir, '*.json')))
        with open(ner_file, encoding='utf-8') as f:
            self.ner_data = json.load(f)
            
        # parameters
        self.MIN_CONTEXT_WORDS = 40
        self.MAX_CONTEXT_WORDS = 100
        
    
    def map_article_ner(self, article):
        # Map NER categories to the entities (links) in Wiki article
        entities = []
        for link in article['links']:
            entity_name = link['link'] #.replace(' ', '_')
            if len(entity_name.split()) != 1:
                continue # Generate a blanks of only 1 word
            if entity_name in self.ner_data and 'NER_Category' in self.ner_data[entity_name]:
                link['category'] = entity_name
                del link['link']
                entities.add(link)
        del article['links']
        articles['entities'] = entities
        return
    
    def generate_for_article(self, article):
        self.map_articles_ner(article)
            
        context_begin_index, next_context_index = 0, 0
        cloze_list = []
        for line in article['body'].split('\n'):
            context_begin_index = next_context_index
            next_context_index += len(line) + 1
            
            if len(line) < self.MIN_CONTEXT_WORDS:
                continue
            
            while len(line) > self.MAX_CONTEXT_WORDS:
                full_stop_index = line.rfind(self.full_stop)
                if full_stop_index > 0:
                    # Sincerely hope that the full stop means end of sentence
                    line = line[:full_stop_index+1]
                else:
                    break
            
            if len(line) <= self.MAX_CONTEXT_WORDS:
                cloze = self.get_cloze_from_context(line, context_begin_index, article['entities'])
                if cloze:
                    cloze_list.append(cloze)
                    break # For now, just generate only cloze per Wiki article
        
        return cloze_list
    
    def generate(self, output_dir):
        save_to = os.path.join(output_dir, 'cloze_set')
        os.makedirs(save_to)
        for article_file in tqdm(self.articles_json, desc='Generating cloze', unit=' articles'):
            with open(article_file, encoding='utf-8') as f:
                article = json.load(f)
            
            cloze = self.generate_for_article(article)
            if cloze: # Save the cloze for this article
                save_filepath = get_verified_path(save_to, article['title'], '.json')
                pretty_write_json(cloze, save_filepath)
        
        # TOOO: Save a consolidated file?
        return
    
if __name__ == '__main__':
    lang_code, ner_file, articles_folder, output_folder = sys.argv[1:]
    g = ClozeGenerator(lang_code, articles_folder, ner_file)
    g.generate(output_folder)
