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
            
        # Parameters
        
        # Range of no. of words to be present in the question
        self.MIN_CONTEXT_WORDS = 30
        self.MAX_CONTEXT_WORDS = 100
        # Minimum no. of -ve options that must atleast be there in the article
        self.MIN_NEGATIVE_CONTEXT_OPTIONS_PER_CLOZE = 2
        # Max. no. of -ve options in the cloze
        self.MAX_NEGATIVE_OPTIONS_PER_CLOZE = 3
        # Should we pick -ve options from global set if above is not satisfied?
        self.ALLOW_GLOBAL_NEGATIVE_OPTIONS = True
        # How many questions per article max?
        self.MAX_CLOZES_PER_ARTICLE = 5
        # For now, generate blanks of only 1 word
        self.MAX_WORDS_IN_ANSWER = 1
        # Replace the right answer with?
        self.MASK_TOKEN = '<MASK>'
        
        self.TRAIN_SPLIT = 0.8
        self.DEV_SPLIT   = 0.1
        self.TEST_SPLIT  = 0.1
        
        # List of all Wiki article files
        self.articles_json = sorted(glob(os.path.join(wiki_articles_dir, '*.json')))
        # Load NER data
        with open(ner_file, encoding='utf-8') as f:
            self.ner_data = json.load(f)
        
        # Create a global map of category->entities
        self.category_to_entities = {}
        for entity, data in self.ner_data.items():
            if 'NER_Category' in data:
                category = data['NER_Category']
                if category not in self.category_to_entities:
                    self.category_to_entities[category] = set()
                entity_name = entity.replace('_', ' ')
                if len(entity_name.split()) > self.MAX_WORDS_IN_ANSWER:
                    continue
                self.category_to_entities[category].add(entity.replace('_', ' '))
    
    def get_params_dict(self):
        # TODO: Make it neat
        return {
            'LANG_CODE': self.LANG_CODE,
            'MIN_CONTEXT_WORDS': self.MIN_CONTEXT_WORDS,
            'MAX_CONTEXT_WORDS': self.MAX_CONTEXT_WORDS,
            'MIN_NEGATIVE_CONTEXT_OPTIONS_PER_CLOZE': self.MIN_NEGATIVE_CONTEXT_OPTIONS_PER_CLOZE,
            'MAX_NEGATIVE_OPTIONS_PER_CLOZE': self.MAX_NEGATIVE_OPTIONS_PER_CLOZE,
            'ALLOW_GLOBAL_NEGATIVE_OPTIONS': self.ALLOW_GLOBAL_NEGATIVE_OPTIONS,
            'MAX_CLOZES_PER_ARTICLE': self.MAX_CLOZES_PER_ARTICLE,
            'MAX_WORDS_IN_ANSWER': self.MAX_WORDS_IN_ANSWER,
            'MASK_TOKEN': self.MASK_TOKEN,
        }
    
    def map_article_ner(self, article):
        # Map NER categories to the entities (links) in Wiki article
        entities, category2entities = [], {}
        for link in article['links']:
            entity_name = link['text']
            entity_fullname = link['link'].replace(' ', '_')
            if len(entity_name.split()) > self.MAX_WORDS_IN_ANSWER:
                continue 
            # Retain only those entities which have a NER category
            if entity_fullname in self.ner_data and 'NER_Category' in self.ner_data[entity_fullname]:
                link['category'] = self.ner_data[entity_fullname]['NER_Category']
                if link['category'] not in category2entities:
                    category2entities[link['category']] = set()
                category2entities[link['category']].add(entity_name)
                self.category_to_entities[link['category']].add(entity_name)
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
            if len(article['category2entities'][category])-1 < self.MIN_NEGATIVE_CONTEXT_OPTIONS_PER_CLOZE:
                continue
            
            # Prepare the cloze now!!
            prefix = context[:entity['begin']-index]
            suffix = context[entity['end']-index:]
            question = prefix + self.MASK_TOKEN + suffix
            positive_option = entity['text']
            
            cloze = {
                'question': question,
                # 'context': context,
                'answer': positive_option,
                'category': category,
                'title': article['title'],
            }
            
            # Get negative options randomly, add the right answer and shuffle
            negative_options = set(article['category2entities'][category])
            negative_options.remove(entity['text'])
            negative_options = list(negative_options)
            random.shuffle(negative_options)
            negative_options = negative_options[:self.MAX_NEGATIVE_OPTIONS_PER_CLOZE]
            
            # Pick negative options from global set if insufficient
            if len(negative_options) < self.MAX_NEGATIVE_OPTIONS_PER_CLOZE and self.ALLOW_GLOBAL_NEGATIVE_OPTIONS:
                global_negative_options = random.sample(self.category_to_entities[category], self.MAX_NEGATIVE_OPTIONS_PER_CLOZE-len(negative_options))
                negative_options += global_negative_options
                cloze['out_of_context_options'] = global_negative_options # For debugging only
            options = negative_options + [positive_option]
            random.shuffle(options)
            cloze['options'] = options
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
    
    def consolidate(self, articles_dir, output_dir, train_split=False):
        
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
        dataset_file = os.path.join(output_dir, 'cloze_dataset.json')
        pretty_write_json(dataset, dataset_file)
        print('Final dataset written to:', dataset_file, '\n')
        
        # Dump a sample of few questions
        random.seed(666)
        random.shuffle(data)
        sample_file = os.path.join(output_dir, 'cloze_sample.json')
        pretty_write_json(data[:20], sample_file)
        print('Sample dataset written to:', sample_file, '\n')
        
        if train_split:
            train_split_len = int(self.TRAIN_SPLIT * len(data))
            pretty_write_json(data[:train_split_len], os.path.join(output_dir, 'cloze_train_set.json'))
            
            dev_split_len = int(self.DEV_SPLIT * len(data))
            pretty_write_json(data[train_split_len:train_split_len+dev_split_len], os.path.join(output_dir, 'cloze_dev_set.json'))
            
            test_split_len = len(data) - (train_split_len+dev_split_len)
            pretty_write_json(data[train_split_len+dev_split_len:], os.path.join(output_dir, 'cloze_test_set.json'))
            
            print('Dataset split into Train-Dev-Test and saved at ', output_dir)
            print('Split ratio %.2f:%.2f:%.2f and count %d:%d:%d\n' %
                  (self.TRAIN_SPLIT, self.DEV_SPLIT, self.TEST_SPLIT, train_split_len, dev_split_len, test_split_len))
        return
    
    def generate(self, output_dir, consolidate=True, train_split=False):
        save_to = os.path.join(output_dir, 'cloze_set')
        os.makedirs(save_to)#, exist_ok=True) # Delete the folder yourself if it exists
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
        print('For individual results, check the folder:', save_to, '\n')
        if consolidate:
            self.consolidate(save_to, output_dir, train_split)
        return

if __name__ == '__main__':
    lang_code, ner_file, articles_folder, output_folder = sys.argv[1:]
    g = ClozeGenerator(lang_code, articles_folder, ner_file)
    g.generate(output_folder)
