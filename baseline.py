#!/usr/bin/env python

# Generate a baseline set of term frequencies to use to give common
# words less weight when analyzing tweets.

import sys, json, time, calendar, os
from collections import namedtuple
from itertools import chain, product

import nltk, twtokenize

def flatten_multi_term(item):
    if type(item) == tuple:
        item = ' '.join(item)
    return item

# Stop words. NLTK provides some in their data set (you need to use
# their nltk.download() tool to get them). They could probably be
# better. Add a few more to deal with obvious missing items,
# punctuation, bad spelling. These aren't actually critical since we compare to a
# baseline data set, but they help cut down the size of the data.
stopwords = nltk.corpus.stopwords.words('english') + [
    '?', '!', ';', '$', '%', '&', '-', '+', '=', '|', '`', '_', '.', '{', '}', ',', '/', '[', ']', '#', '@', ':', "'", '(', ')', '^', '~', '*', #punctuation
    'c', 'u', 'r', 'o', 'd', 'e', 'f', 'g', 'v', 'h', 'x', 'w', 'j', 'y', 'k', 'l', 'z', 'm', 'n', 'p', 'b', 'q' # bad spelling
    ]
# Some more things that our processing doesn't catch, often weird
# parts of words like 't, web things like http, or bad conversions
# like < and > to lt and gt
stopwords = stopwords + [
    'http', 'gt', 'lt', "'t", 'la', "'s", "''", 'amp', "n't", "'m", "...", "de", "``"
]
stopwords = set(stopwords)

def splitlist(l, on):
    '''Split a list into a sublists when any element in 'on' is found,
    removing that element in the process.'''
    last_idx = 0
    idx = 0
    while idx < len(l):
        while idx < len(l):
            if l[idx] in on:
                break
            idx += 1
        yield l[last_idx:idx]
        idx += 1
        last_idx = idx

def tokenize_and_ngram(text):
    tokens = [x.lower() for x in twtokenize.word_tokenize(text)]
    # Split into sublists using stopwords. This keeps us from
    # generating n-grams from words that aren't actually next
    # to each other. This step also removes the stopwords
    tokens = list(splitlist(tokens, stopwords))
    bgrams = [nltk.ibigrams(subtokens) for subtokens in tokens]
    tgrams = [nltk.itrigrams(subtokens) for subtokens in tokens]
    terms = list(chain(*(tokens + bgrams + tgrams)))
    return terms

tweet_file = os.path.abspath(sys.argv[1])

term_freqs = {}
# Count
total = 0
with open(tweet_file, 'r') as fp:
    for line in fp:
        tweet = json.loads(line)
        terms = tokenize_and_ngram(tweet['text'])
        for term in terms:
            term = flatten_multi_term(term)
            term_freqs[term] = term_freqs.get(term, 0) + 1
            total += 1

# Normalize
term_freqs = dict([(k,float(v)/total) for k,v in term_freqs.iteritems()])

with open(tweet_file + '.freq', 'w') as fp:
    json.dump(term_freqs, fp)
