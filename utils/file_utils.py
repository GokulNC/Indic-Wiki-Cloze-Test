import json
import sys
import os

def pretty_write_json(data, outfile, sort_keys=False):
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=sort_keys)

INVALID_FILENAME_CHARS = '<>:"/\\|?*'
def get_valid_filename(filename):
    # Note: Tested only on Windows
    return ''.join(c for c in filename if c not in INVALID_FILENAME_CHARS)

MAX_PATH_LENGTH_BYTES = 255
def get_verified_path(folder, filename, extension_with_dot):
    # assert sys.getsizeof(folder) + sys.getsizeof(extension_with_dot) < MAX_PATH_LENGTH_BYTES
    filename = get_valid_filename(filename)
    pathname = os.path.abspath(os.path.join(folder, filename))
    max_pathname_bytes = MAX_PATH_LENGTH_BYTES - sys.getsizeof(extension_with_dot)
    if sys.getsizeof(pathname) > max_pathname_bytes:
        pathname = bytearray(pathname.encode('utf8'))[:max_pathname_bytes].decode(errors='ignore')
    return pathname + extension_with_dot
