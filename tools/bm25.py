
from rank_bm25 import BM25Okapi
import os
from nltk.tokenize import word_tokenize
import nltk
nltk.download('punkt')

def get_all_files(directory):
    all_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files

def read_files(files):
    corpus = []
    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                corpus.append(f.read())
        except:
            pass
    return corpus

def retrieve_files(query, top_n=5):
    directory = '/workspaces/qb_ai'
    files = get_all_files(directory)
    corpus = read_files(files)
    
    tokenized_corpus = [word_tokenize(doc.lower()) for doc in corpus]
    
    bm25 = BM25Okapi(tokenized_corpus)
    
    tokenized_query = word_tokenize(query.lower())
    
    doc_scores = bm25.get_scores(tokenized_query)
    
    top_n_indices = doc_scores.argsort()[-top_n:][::-1]
    
    return [files[i] for i in top_n_indices]

def get_tools():
    return [
        {
            "function_declarations": [{
                "name": "retrieve_files",
                "description": "Retrieve files using BM25.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for."
                        },
                        "top_n": {
                            "type": "integer",
                            "description": "The number of files to retrieve."
                        }
                    },
                    "required": ["query"]
                }
            }]
        }
    ]
