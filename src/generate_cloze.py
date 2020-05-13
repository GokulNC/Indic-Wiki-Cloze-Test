'''
Code to generate cloze task dataset given the list of all Wiki articles and Entity-to-category NER map.

USAGE:
$ <script.py> <lang_code> <ner_file> <articles_folder> <output_folder>

EXAMPLE:
$ python src/generate_cloze.py hi output/hi/ner_list.json output/hi/articles/ output/hi/
'''

import os, sys
import json
import random
import traceback
from glob import glob
from tqdm import tqdm
from datetime import datetime

from utils.lang_utils import EOS_DELIMITERS
from utils.file_utils import pretty_write_json, get_verified_path

class ClozeGenerator():
    def __init__(self, lang_code, wiki_articles_dir, ner_file):
        self.LANG_CODE = lang_code
        self.full_stop = EOS_DELIMITERS[lang_code]
        
        self.articles_json = sorted(glob(os.path.join(wiki_articles_dir, '*.json')))
        with open(ner_file, encoding='utf-8') as f:
            self.ner_data = json.load(f)
            
        # parameters
        self.MIN_CONTEXT_WORDS = 30
        self.MAX_CONTEXT_WORDS = 100
        self.MIN_OPTIONS_PER_CLOZE = 3
        self.MAX_NEGATIVE_OPTIONS_PER_CLOZE = 4
        self.MAX_CLOZES_PER_ARTICLE = 5
        self.MASK_TOKEN = '<MASK>'
    
    def get_params_dict(self):
        # TODO: Make it neat
        return {
            'LANG_CODE': self.LANG_CODE,
            'MIN_CONTEXT_WORDS': self.MIN_CONTEXT_WORDS,
            'MAX_CONTEXT_WORDS': self.MAX_CONTEXT_WORDS,
            'MIN_OPTIONS_PER_CLOZE': self.MIN_OPTIONS_PER_CLOZE,
            'MAX_NEGATIVE_OPTIONS_PER_CLOZE': self.MAX_NEGATIVE_OPTIONS_PER_CLOZE,
            'MAX_CLOZES_PER_ARTICLE': self.MAX_CLOZES_PER_ARTICLE,
            'MASK_TOKEN': self.MASK_TOKEN,
        }
    
    def map_article_ner(self, article):
        # Map NER categories to the entities (links) in Wiki article
        entities, category2entities = [], {}
        for link in article['links']:
            entity_name = link['text']
            entity_fullname = link['link'].replace(' ', '_')
            if len(entity_name.split()) != 1: # For now, generate blanks of only 1 word
                continue 
            # Retain only those entities which have a NER category
            if entity_fullname in self.ner_data and 'NER_Category' in self.ner_data[entity_fullname]:
                link['category'] = self.ner_data[entity_fullname]['NER_Category']
                if link['category'] in category2entities:
                    category2entities[link['category']].add(entity_name)
                else:
                    category2entities[link['category']] = set([entity_name])
                del link['link']
                entities.append(link)
        del article['links']
        article['entities'] = entities
        article['category2entities'] = category2entities
        return
    
    def get_cloze_from_context(self, context, index, article):
        end_index = index + len(context)
        category2entities = article['category2entities']
        for entity in article['entities']: #Assumes sorted based on begin index
            
            # Check boundary cases
            if entity['begin'] < index:
                continue
            if entity['begin'] + len(entity['text']) > end_index:
                break
            
            # Ok, now see if we can make this entity as a blank
            # How? Check if the article has some entities of same category for negative examples
            category = entity['category']
            if len(article['category2entities'][category]) < self.MIN_OPTIONS_PER_CLOZE:
                continue
            
            # Prepare the cloze now!!
            prefix = context[:entity['begin']-index]
            suffix = context[entity['end']-index:]
            question = prefix + self.MASK_TOKEN + suffix
            # Get negative options randomly, add the right answer and shuffle
            negative_options = set(article['category2entities'][category])
            negative_options.remove(entity['text'])
            negative_options = list(negative_options)
            random.shuffle(negative_options)
            negative_options = negative_options[:self.MAX_NEGATIVE_OPTIONS_PER_CLOZE]
            options = negative_options + [entity['text']]
            random.shuffle(options)
            cloze = {
                'question': question,
                # 'context': context,
                'options': options,
                'answer': entity['text'],
                'category': category,
                'title': article['title'],
            }
            return cloze
            
        return {}
    
    def generate_for_article(self, article):
        self.map_article_ner(article)
            
        context_begin_index, next_context_index = 0, 0
        cloze_list = []
        for line in article['body'].split('\n'):
            context_begin_index = next_context_index
            next_context_index += len(line) + 1
            
            # Skip if the context is not big enough
            if len(line.split()) < self.MIN_CONTEXT_WORDS:
                continue
            
            # Remove few sentences from the end if context is too big
            while len(line.split()) > self.MAX_CONTEXT_WORDS:
                full_stop_index = line.rfind(self.full_stop)
                if full_stop_index == len(line) - 1:
                    full_stop_index = line[:full_stop_index].rfind(self.full_stop)
                if full_stop_index > 0:
                    # Sincerely hope that the full stop means end of sentence
                    line = line[:full_stop_index+1]
                else:
                    break
            
            if len(line.split()) <= self.MAX_CONTEXT_WORDS:
                cloze = self.get_cloze_from_context(line, context_begin_index, article)
                if cloze:
                    cloze_list.append(cloze)
                    if len(cloze_list) >= self.MAX_CLOZES_PER_ARTICLE:
                        break
        
        return cloze_list
    
    def consolidate(self, articles_dir, outfile):
        article_files = sorted(glob(os.path.join(articles_dir, '*.json')))
        data = [] #WARN: Can be RAM consuming.
        for article_file in tqdm(article_files, desc='Consolidating', unit=' articles'):
            with open(article_file, encoding='utf-8') as f:
                cloze_list = json.load(f)
            data += cloze_list
        
        dataset = {
            'params': self.get_params_dict(),
            'metadata': {
                'TOTAL_CLOZES': len(data),
                'PROCESSED_WIKI_ARTICLES': len(self.articles_json),
                'GENERATED_TIMESTAMP': str(datetime.now())
            },
            'cloze_data': data
        }
        pretty_write_json(dataset, outfile)
        return
    
    def generate(self, output_dir, consolidate=True):
        save_to = os.path.join(output_dir, 'cloze_set')
        os.makedirs(save_to, exist_ok=True)
        total_data_count = 0
        for article_file in tqdm(self.articles_json, desc='Generating cloze', unit=' articles'):
            try:
                with open(article_file, encoding='utf-8') as f:
                    article = json.load(f)
            except:
                print(traceback.format_exc())
                print('Unable to parse:', article_file)
                continue
            
            cloze_list = self.generate_for_article(article)
            if cloze_list: # Save the cloze for this article
                save_filepath = get_verified_path(save_to, article['title'], '.json')
                pretty_write_json(cloze_list, save_filepath)
                total_data_count += len(cloze_list)
        
        print('SUCCESS: Generated a total of %d cloze questions!' % total_data_count)
        print('For individual results, check the folder:', save_to)
        if consolidate:
            dataset_file = os.path.join(output_dir, 'cloze_dataset.json')
            self.consolidate(save_to, dataset_file)
            print('Final dataset written to:', dataset_file)
        return

if __name__ == '__main__':
    lang_code, ner_file, articles_folder, output_folder = sys.argv[1:]
    g = ClozeGenerator(lang_code, articles_folder, ner_file)
    g.generate(output_folder)
