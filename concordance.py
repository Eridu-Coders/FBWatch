#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

# sudo pip install -U nltk
# from http://www.nltk.org/install.html

import sys
import re

from nltk import sent_tokenize, word_tokenize, pos_tag
from nltk.stem import WordNetLemmatizer

import mysql.connector

import urllib.error
import urllib.request
import time
import json

from lxml import html

# ---------------------------------------------------- Globals ---------------------------------------------------------
g_connectorRead = None
g_connectorWrite = None
g_connectorOriginWrite = None

g_tldRe = []
g_contractionRe = []

g_contractions = {
    "he ain't": "he is not",
    "I ain't": "I am not",
    "you ain't": "you are not",
    "we ain't": "We are not",
    "they ain't": "they are not",
    "ain't": "is not",
    "aren't": "are not",
    "can't": "cannot",
    "can't've": "cannot have",
    "'cause": "because",
    "could've": "could have",
    "couldn't": "could not",
    "couldn't've": "could not have",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "do not",
    "hadn't": "had not",
    "hadn't've": "had not have",
    "hasn't": "has not",
    "haven't": "have not",
    "he'd": "he would",
    "he'd've": "he would have",
    "he'll": "he will",
    "he'll've": "he will have",
    "he's": "he is",
    "how'd": "how did",
    "how'd'y": "how do you",
    "how'll": "how will",
    "how's": "how is",
    "I'd": "I would",
    "I'd've": "I would have",
    "I'll": "I will",
    "I'll've": "I will have",
    "I'm": "I am",
    "I've": "I have",
    "isn't": "is not",
    "it'd": "it would",
    "it'd've": "it would have",
    "it'll": "it will",
    "it'll've": "it will have",
    "it's": "it is",
    "let's": "let us",
    "ma'am": "madam",
    "mayn't": "may not",
    "might've": "might have",
    "mightn't": "might not",
    "mightn't've": "might not have",
    "must've": "must have",
    "mustn't": "must not",
    "mustn't've": "must not have",
    "needn't": "need not",
    "needn't've": "need not have",
    "o'clock": "of the clock",
    "oughtn't": "ought not",
    "oughtn't've": "ought not have",
    "shan't": "shall not",
    "sha'n't": "shall not",
    "shan't've": "shall not have",
    "she'd": "she would",
    "she'd've": "she would have",
    "she'll": "she will",
    "she'll've": "she will have",
    "she's": "she is",
    "should've": "should have",
    "shouldn't": "should not",
    "shouldn't've": "should not have",
    "so've": "so have",
    "so's": "so is",
    "that'd": "that would",
    "that'd've": "that would have",
    "that's": "that is",
    "there'd": "there would",
    "there'd've": "there would have",
    "there's": "there is",
    "they'd": "they would",
    "they'd've": "they would have",
    "they'll": "they will",
    "they'll've": "they will have",
    "they're": "they are",
    "they've": "they have",
    "to've": "to have",
    "wasn't": "was not",
    "we'd": "we would",
    "we'd've": "we would have",
    "we'll": "we will",
    "we'll've": "we will have",
    "we're": "we are",
    "we've": "we have",
    "weren't": "were not",
    "what'll": "what will",
    "what'll've": "what will have",
    "what're": "what are",
    "what's": "what is",
    "what've": "what have",
    "when's": "when is",
    "when've": "when have",
    "where'd": "where did",
    "where's": "where is",
    "where've": "where have",
    "who'll": "who will",
    "who'll've": "who will have",
    "who's": "who is",
    "who've": "who have",
    "why's": "why is",
    "why've": "why have",
    "will've": "will have",
    "won't": "will not",
    "won't've": "will not have",
    "would've": "would have",
    "wouldn't": "would not",
    "wouldn't've": "would not have",
    "y'all": "you all",
    "y'all'd": "you all would",
    "y'all'd've": "you all would have",
    "y'all're": "you all are",
    "y'all've": "you all have",
    "you'd": "you would",
    "you'd've": "you would have",
    "you'll": "you will",
    "you'll've": "you will have",
    "you're": "you are",
    "you've": "you have"
}
# ---------------------------------------------------- Functions -------------------------------------------------------
def cleanForInsert(s):
    r = re.sub('"', '""', s)
    r = re.sub(r'\\', r'\\\\', r)

    return r

def storeConc(p_idObjInternal, p_before, p_word, p_lemma, p_tag, p_after, p_context):
    l_lenLimit = 50

    if len(p_word) > l_lenLimit or len(p_lemma) > l_lenLimit:
        return

    l_cursor = g_connectorWrite.cursor()
    l_query = """
        INSERT INTO `TB_CONCORD`(`ID_OBJ_INTERNAL`,`TX_BEFORE`,`ST_WORD`,`ST_LEMMA`,`ST_TAG`,`TX_AFTER`,`TX_CONTEXT`)
        VALUES( {0}, "{1}", "{2}", "{3}", "{4}", "{5}", "{6}" )
    """.format(
        p_idObjInternal,
        cleanForInsert(p_before),
        cleanForInsert(p_word),
        cleanForInsert(p_lemma),
        cleanForInsert(p_tag),
        cleanForInsert(p_after),
        cleanForInsert(json.dumps(p_context))
    )

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connectorWrite.commit()
    except Exception as e:
        print('TB_CONCORD Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def flagDone(p_idObjInternal):
    l_cursor = g_connectorOriginWrite.cursor()
    l_query = """
        UPDATE `TB_OBJ`
        SET F_WORD_SPLIT = "X"
        WHERE `ID_INTERNAL` = {0};
    """.format(p_idObjInternal)

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connectorWrite.commit()
    except Exception as e:
        print('TB_CONCORD Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def cleanText(p_t1, p_t2, p_t3, p_t4, p_t5, p_verbose=False):
    l_concat = '{0}¤¤¤xXx¤¤¤{1}¤¤¤xXx¤¤¤{2}¤¤¤xXx¤¤¤{3}¤¤¤xXx¤¤¤{4}¤¤¤xXx¤¤¤' \
        .format(p_t1, p_t2, p_t3, p_t4, p_t5)

    if p_verbose:
        print('1:', l_concat)

    l_concat = re.sub(r'http://', '¤¤¤HTTP¤¤¤', l_concat)
    l_concat = re.sub(r'https://', '¤¤¤HTTPS¤¤¤', l_concat)

    # ;-)
    l_concat = re.sub(r';-\)', '¤¤¤SMILEY1¤¤¤', l_concat)
    l_concat = re.sub(r':-\)', '¤¤¤SMILEY2¤¤¤', l_concat)
    l_concat = re.sub(r';\)', '¤¤¤SMILEY1¤¤¤', l_concat)
    l_concat = re.sub(r':\)', '¤¤¤SMILEY2¤¤¤', l_concat)
    l_concat = re.sub(r';\)\)', '¤¤¤SMILEY3¤¤¤', l_concat)
    l_concat = re.sub(r':\)\)', '¤¤¤SMILEY4¤¤¤', l_concat)
    l_concat = re.sub(r';D', '¤¤¤SMILEY5¤¤¤', l_concat)
    l_concat = re.sub(r':D', '¤¤¤SMILEY6¤¤¤', l_concat)
    l_concat = re.sub(r';-D', '¤¤¤SMILEY5¤¤¤', l_concat)
    l_concat = re.sub(r':-D', '¤¤¤SMILEY6¤¤¤', l_concat)

    if p_verbose:
        print('2:', l_concat)

    for l_re in g_tldRe:
        l_concat = l_re.sub(r'\1¤¤¤DOT¤¤¤\2\3', l_concat)

    for i in range(10):
        l_concat = re.sub(r'(\w+)\.(\w+)¤¤¤DOT¤¤¤', r'\1¤¤¤DOT¤¤¤\2¤¤¤DOT¤¤¤', l_concat)

    for i in range(3):
        l_concat = re.sub(r'(^|\W)(\w)\.(\w)(\W|$)', r'\1\2¤¤¤DOT¤¤¤\3\4', l_concat)

    if p_verbose:
        print('3:', l_concat)

    l_concat = re.sub(r'\s+', ' ', l_concat)

    l_concat = re.sub(r'¤¤¤xXx¤¤¤[\.\?\!]+', r'¤¤¤xXx¤¤¤', l_concat)
    l_concat = re.sub(r'([\.\?\!])¤¤¤xXx¤¤¤', r'\1', l_concat)
    l_concat = re.sub(r'¤¤¤xXx¤¤¤', r'.', l_concat)

    l_concat = re.sub(r'\s+([\.\?\!])', r'\1', l_concat)
    l_concat = re.sub(r'([\.\?\!])\s+', r'\1', l_concat)
    l_concat = re.sub(r'[\.\?\!]+([\.\?\!])', r'\1', l_concat)
    l_concat = re.sub(r'^[\.\?\!]+', '', l_concat)
    l_concat = re.sub(r'([\.\?\!])([^\'"])', r'\1 \2', l_concat).strip()

    if p_verbose:
        print('4:', l_concat)

    l_concat = re.sub(r'\s+([,:;])', r'\1', l_concat)
    l_concat = re.sub(r'(?P<punct>[,:;])(?P=punct)+', r'\1', l_concat)
    l_concat = re.sub(r'([,:;])(\S)', r'\1 \2', l_concat)

    l_concat = re.sub(r'\s+(\)\])', r'\1', l_concat)
    l_concat = re.sub(r'(\(\[)\s+', r'\1', l_concat)
    l_concat = re.sub(r'(\S)(\(\[)', r'\1 \2', l_concat)
    l_concat = re.sub(r'(\)\])(\S)', r'\1 \2', l_concat)

    if p_verbose:
        print('5:', l_concat)

    l_concat = re.sub('¤¤¤SMILEY1¤¤¤', ';-)', l_concat)
    l_concat = re.sub('¤¤¤SMILEY2¤¤¤', ':-)', l_concat)
    l_concat = re.sub('¤¤¤SMILEY3¤¤¤', ';))', l_concat)
    l_concat = re.sub('¤¤¤SMILEY4¤¤¤', ':))', l_concat)
    l_concat = re.sub('¤¤¤SMILEY5¤¤¤', ';-D', l_concat)
    l_concat = re.sub('¤¤¤SMILEY6¤¤¤', ':-D', l_concat)
    l_concat = re.sub('¤¤¤DOT¤¤¤', '.', l_concat)

    l_concat = re.sub('¤¤¤HTTP¤¤¤', r'http://', l_concat)
    l_concat = re.sub('¤¤¤HTTPS¤¤¤', r'https://', l_concat)

    if p_verbose:
        print('6:', l_concat)

    for l_re, l_sub in g_contractionRe:
        l_concat = l_re.sub(l_sub, l_concat)

    if p_verbose:
        print('F:', l_concat)

    return l_concat

def compileRe(p_verbose=False):
    global g_tldRe
    global g_contractionRe

    l_finished = False
    l_extlist = ['com', 'org', 'net', 'edu', 'gov', 'mil', 'fr']
    l_trycount = 0
    while not l_finished and l_trycount < 10:
        try:
            l_response = urllib.request.urlopen(
                'http://www.iana.org/domains/root/db', timeout=10).read().decode('utf-8').strip()

            l_tree = html.fromstring(l_response)

            l_extlist = \
                [re.sub(r'^\.', '', f.text_content()) for f in l_tree.xpath('//td/span[@class="domain tld"]/a')]

            l_finished = True

        except Exception as e:
            time.sleep(5)
            l_trycount += 1

    if p_verbose:
        print('l_extlist:', l_extlist)
    print('l_extlist count:', len(l_extlist))

    # re.sub(r'(\w+)\.{0}(\W|$)'.format(l_ext), r'\1¤¤¤DOT¤¤¤{0}\2'.format(l_ext), l_concat)
    for l_ext in l_extlist:
        g_tldRe += [re.compile(r'(\w+)\.({0})(\W|$)'.format(l_ext))]

    for l_contr in g_contractions.keys():
        g_contractionRe += [
            (re.compile(l_contr), g_contractions[l_contr]),
            (re.compile(l_contr.capitalize()), g_contractions[l_contr].capitalize()) ]

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Build concordance from object texts                        |')
    print('|                                                            |')
    print('| v. 1.1 - 28/04/2016                                        |')
    print('+------------------------------------------------------------+')

    compileRe()

    # used to read from TB_OBJ
    g_connectorRead = mysql.connector.connect(
        user='root',
        password='murugan!',
        host='192.168.0.52',
        database='FBWatch')
    # used to write back to TB_OBJ (F_WORD_SPLIT update)
    g_connectorOriginWrite = mysql.connector.connect(
        user='root',
        password='murugan!',
        host='192.168.0.52',
        database='FBWatch')
    # used to write to TB_CONCORD
    g_connectorWrite = mysql.connector.connect(
        user='root',
        password='murugan!',
        host='192.168.0.52',
        database='FBWatch')

    l_finished = False
    while not l_finished:
        l_cursor = g_connectorRead.cursor(buffered=True)

        # read non page objects from TB_OBJ in 100 row batches
        l_query = """
            SELECT
                `ID_INTERNAL`
                ,`ST_FB_TYPE`
                ,`TX_NAME`
                ,`TX_CAPTION`
                ,`TX_DESCRIPTION`
                ,`TX_STORY`
                ,`TX_MESSAGE`
            FROM
                `TB_OBJ`
            WHERE
                `ST_TYPE` != 'Page'
                AND `F_WORD_SPLIT` is null
            LIMIT 100;
        """

        try:
            l_cursor.execute(l_query)

            if l_cursor.rowcount == 0:
                l_finished = True
                break

            l_wnl = WordNetLemmatizer()

            print('*** NEW BATCH ***')
            for l_idInternal, l_type, l_name, l_caption, l_description, l_story, l_message in l_cursor:
                print('--------------------------------------------------')
                print('l_type       :', l_type)
                print('l_name       :', l_name)
                print('l_caption    :', l_caption)
                print('l_description:', l_description)
                print('l_story      :', l_story)
                print('l_message    :', l_message)

                l_concat = cleanText(l_name, l_caption, l_description, l_story, l_message)
                print('l_concat     :', l_concat)

                # POS tagging
                l_tag = [pos_tag(word_tokenize(s)) for s in sent_tokenize(l_concat)]

                # lemmatization
                l_tagLemma = [[(w[0], l_wnl.lemmatize(w[0], pos='v'), w[1]) for w in s] for s in l_tag]

                # print(l_tagLemma)

                for s in l_tagLemma:
                    l_punct = ''

                    # punctuation removal
                    l_sPunct = []
                    for w in s[::-1]:
                        if re.match('^\W$', w[0]):
                            l_punct = w[0]
                        else:
                            l_sPunct += [(w[0]+l_punct, w[1], w[2])]
                            l_punct = ''

                    l_sPunct = l_sPunct[::-1]

                    print('   +++++++++++++++++++++++')
                    i = 0
                    r = 3
                    for w in l_sPunct:
                        # Neighborhood
                        if i < r:
                            l_begin = 0
                            l_end = min(len(l_sPunct)-1, 2*r)
                        elif i > len(l_sPunct)-r-1:
                            l_end = len(l_sPunct)-1
                            l_begin = max(0, l_end - 2*r)
                        else:
                            l_begin = i-r
                            l_end = i+r

                        # print(l_sPunct[l_begin:i], w, l_sPunct[i+1:l_end+1])

                        l_segBefore = l_sPunct[l_begin:i]
                        l_segAfter = l_sPunct[i+1:l_end+1]

                        l_before = ' '.join([x[0] for x in l_segBefore])
                        l_after = ' '.join([x[0] for x in l_segAfter])

                        print('   {0:<30} {1:<20} {2:<30}'.format(l_before, w[0], l_after), l_segAfter)
                        storeConc(l_idInternal, l_before, w[0], w[1].lower(), w[2], l_after,
                                  (l_segBefore, w, l_segAfter))

                        i += 1

                print('--------------------------------------------------')
                print('l_type       :', l_type)
                print('l_name       :', l_name)
                print('l_caption    :', l_caption)
                print('l_description:', l_description)
                print('l_story      :', l_story)
                print('l_message    :', l_message)

                # Mark this object as done
                flagDone(l_idInternal)

        except Exception as e:
            print('Unknown Exception: {0}'.format(repr(e)))
            print(l_query)
            sys.exit()

        l_cursor.close()