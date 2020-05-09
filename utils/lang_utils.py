'''
Language Utilities
'''
# TODO: Ensure all languages of the Indian subcontinent is supported

# End of Sentence Full Stops for different language scripts
EOS_DELIMITERS = {
    'hi': '।',
    'or': '।',
    'as': '।',
    'bn': '।',
    'pa': '।',
    'bh': '।',
    # Even though Marathi is Devanagari, it uses full-stop. He is the reason the keys are lang_codes instead of script names
    'mr': '.', 
    'gu': '.',
    'kn': '.',
    'te': '.',
    'ta': '.',
    'ml': '.'
}
