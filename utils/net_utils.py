from threading import Thread
from requests import get
from time import sleep
from tqdm import tqdm

class URLThread(Thread):
    def __init__(self, url, timeout):
        super(URLThread, self).__init__()
        self.url = url
        self.response = None
        self.max_timeout = timeout if timeout else None
        # TODO: Implement retries?

    def run(self):
        self.response = get(self.url, timeout=self.max_timeout)

def multi_get(uris, timeout=0.0):
    # Inspired: github.com/divkakwani/webcorpus/blob/master/webcorpus/processors/headline-pred.py#L38
    threads = [URLThread(uri, timeout) for uri in uris]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    return [(x.url, x.response) for x in threads]

def multi_get_batch(uris, batch_size, timeout=0.0):
    num_batches = (len(uris) + batch_size) // batch_size
    results = []
    for i in tqdm(range(num_batches), desc='Batched querying', unit='batch'):
        results += multi_get(uris[i*batch_size : (i+1)*batch_size], timeout)
    return results
