## Wikipedia-based Cloze Test for Indian Languages

### Installing
- `sudo apt install bzip2 wget python3 python3-pip byobu git`
- `git clone <repo>` and `cd <repo>`
- `pip3 install -r requirements.txt`
- In every new terminal, do:
  ```bash
  export PYTHONPATH=`pwd`:$PYTHONPATH
  ```

### Getting Wikipedia Dumps
Get the XML dump specific to your languge from [Wikipedia Dumps](dumps.wikimedia.org/)  
For instance, to download the Hindi Wikipedia Dumps from 01-May-2020:
```bash
wget 'https://dumps.wikimedia.org/hiwiki/20200501/hiwiki-20200501-pages-articles-multistream.xml.bz2'
```

To extract the dumps to get XML file:
```bash
bzip2 -dk hiwiki-20200501-pages-articles-multistream.xml.bz2
```
### Processing the Wikipedia XML

To process the dumps and convert all the articles to JSON and also dump the links, do:
```bash
python3 src/wiki2json.py <lang_code> <xml_file> <output_folder>
```

For example:
```bash
python3 src/wiki2json.py hi data/hiwiki-20200501-pages-articles-multistream.xml output/hi/
```

This will dump the articles to a directory in the `<output_folder>` called `articles` and another file called `page_titles.txt` containing all possible Wikipedia entities.

### Performing NER using WikiData
To find the NER categories of all the Wikipedia page titles (from a `txt` file) using WikiData:

```bash
python3 src/wiki2ner.py <lang_code> <txt_file> <output_folder>
```

For example:
```bash
python3 src/wiki2ner.py hi output/hi/page_titles.txt output/hi/
```

This will dump a file to the `output_folder` called `ner_list.json` which contains the list of all entitity name, WikiData QID and the NER category.

As of now, the supported categories are: (can also be found in [wikidata_sparql.py](src/wikidata_sparql.py))
- Person
- Organization
- Location
- Event

### Creating the Cloze-Test Dataset
<-- **Work In Progress** -->
