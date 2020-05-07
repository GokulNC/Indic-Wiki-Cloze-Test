'''
To process the Wikipedia XML Dump and store the articles (as JSONs) & links.

USAGE:
$ <script.py> <lang_code> <xml_file> <output_folder>

EXAMPLE:
$ python wiki2json.py hi data/hiwiki-20200501-pages-articles-multistream.xml output/hi/
'''

import os, sys, traceback
from os.path import abspath
from tqdm import tqdm

from utils.wiki_dump_reader import Cleaner, iterate
from utils.file_utils import pretty_write_json, get_verified_path

class WikipediaXML2JSON():
    def __init__(self, wiki_xml, lang_code):
        self.wiki_xml = wiki_xml
        self.lang_code = lang_code
    
    def process_wiki_xml(self, save_to):
        os.makedirs(save_to, exist_ok=True)
        articles_path = os.path.join(save_to, 'articles')
        os.makedirs(articles_path, exist_ok=True)
        cleaner = Cleaner()
        page_titles = set()
        for title, text in tqdm(iterate(self.wiki_xml), desc='Wikipedia processing', unit=' articles'):
            # Clean each article to get plain-text and links
            try:
                text = cleaner.clean_text(text)
                cleaned_text, links = cleaner.build_links(text)
            except:
                print(traceback.format_exc())
                print('Failed to parse article:', title)
                continue
            
            # Store article as JSON. Note: 255 is max_path_length for Linux
            json_path = get_verified_path(articles_path, title, '.json')
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
        
if __name__ == '__main__':
    lang_code, xml_file, output_folder = sys.argv[1:]
    processor = WikipediaXML2JSON(xml_file, lang_code)
    processor.process_wiki_xml(output_folder)
    