import json

def pretty_write_json(data, outfile, sort_keys=False):
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=sort_keys)

INVALID_FILENAME_CHARS = '<>:"/\\|?*'
def get_valid_filename(filename):
    # Note: Tested only on Windows
    return ''.join(c for c in filename if c not in INVALID_FILENAME_CHARS)
