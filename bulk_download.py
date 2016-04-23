#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import urllib.request
import urllib.error
import json
import re
import time
import sys
import datetime

import mysql.connector

from login_as import loginAs

# ---------------------------------------------------- Globals ---------------------------------------------------------
G_MAX_POST = 300
G_LIMIT = 100
G_WAIT_FB = 60 * 60
G_WAIT_FB_SESSION = 60 * 10

g_connector = None

g_objectFound = 0
g_objectStored = 0

g_FBToken = None

g_user = 'john.braekernell@yahoo.com'
g_pass = '15Eyyaka'

g_errFile = None

# ---------------------------------------------------- Functions -------------------------------------------------------
def cleanForInsert(s):
    r = re.sub('"', '""', s)
    r = re.sub(r'\\', r'\\\\', r)

    return r

def storeObject(p_padding, p_type, p_id, p_parentId, p_pageId, p_date, p_text1, p_text2, p_userId=''):
    global g_objectStored
    global g_objectFound

    g_objectFound += 1

    # date format: 2016-04-22T12:03:06+0000 ---> 2016-04-22 12:03:06
    l_date = re.sub('T', ' ', p_date)
    l_date = re.sub(r'\+\d+$', '', l_date)

    l_cursor = g_connector.cursor()

    l_query = """
        INSERT INTO TB_OBJ(`ID`, `ID_FATHER`, `ID_PAGE`, `DT_CRE`, `ST_TYPE`, `TX_1`, `TX_2`, `ID_USER`)
        VALUES( "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}", "{7}" )
    """.format(
        p_id,
        p_parentId,
        p_pageId,
        l_date,
        p_type,
        cleanForInsert(p_text1),
        cleanForInsert(p_text2),
        p_userId
    )

    # print(l_query)

    try:
        l_cursor.execute(l_query)
        g_connector.commit()
        g_objectStored += 1
    except mysql.connector.errors.IntegrityError:
        print('{0}Object already in DB'.format(p_padding))
    except Exception as e:
        print('TB_OBJ Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    print('{0}Object counts: {1} found / {2} stored'.format(
        p_padding, g_objectFound, g_objectStored))

    l_cursor.close()

def storeUser(p_id, p_name, p_date, p_padding):
    # date format: 2016-04-22T12:03:06+0000 ---> 2016-04-22 12:03:06
    l_date = re.sub('T', ' ', p_date)
    l_date = re.sub(r'\+\d+$', '', l_date)

    l_cursor = g_connector.cursor()

    l_query = """
        INSERT INTO TB_USER(`ID`, `ST_NAME`, `DT_CRE`, `DT_MSG`)
        VALUES( "{0}", "{1}", "{2}", "{3}" )
    """.format(
        p_id,
        cleanForInsert(p_name),
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        l_date,
    )

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connector.commit()
    except mysql.connector.errors.IntegrityError:
        print('{0}User already known'.format(p_padding))
    except Exception as e:
        print('TB_USER Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def getOptionalField(p_json, p_field):
    l_value = ''
    l_valueShort = ''

    if p_field in p_json.keys():
        l_value = re.sub('\s+', ' ', p_json[p_field]).strip()
        if len(l_value) > 100:
            l_valueShort = l_value[0:100] + ' ... ({0})'.format(len(l_value))
        else:
            l_valueShort = l_value

    return l_value, l_valueShort

def getPostsFromPage(p_id):
    # get list of posts in this page's feed
    l_request = 'https://graph.facebook.com/v2.6/{0}/feed?limit={2}&access_token={1}'.format(
        p_id, g_FBToken, G_LIMIT)
    # print('   l_request:', l_request)
    l_response = performRequest(l_request)

    l_responseData = json.loads(l_response)
    # print('   Paging:', l_responseData['paging'])
    print('   Latest date:', l_responseData['data'][0]['created_time'])

    l_postCount = 0
    while l_postCount < G_MAX_POST:
        for l_post in l_responseData['data']:
            l_postId = l_post['id']
            l_postDate = l_post['created_time']
            print('   =====[ {0} ]======================================================'.format(l_postCount))
            print('   id      :', l_postId)
            print('   date    :', l_postDate)

            # 2016-04-22T12:03:06+0000
            l_msgDate = datetime.datetime.strptime(
                re.sub(r'\+\d+$', '', l_postDate), '%Y-%m-%dT%H:%M:%S')
            print('   date (P):', l_msgDate)

            if (l_msgDate - datetime.datetime.now()).days > 8:
                l_postCount = G_MAX_POST
                break

            l_story, l_storyShort = getOptionalField(l_post, 'story')
            l_message, l_messageShort = getOptionalField(l_post, 'message')

            print('   story   :', l_storyShort)
            print('   message :', l_messageShort)

            # store post information
            storeObject('   ', 'Post', l_postId, p_id, p_id, l_postDate, l_story, l_message)

            # get comments
            getComments(l_postId, p_id, 0)

            l_postCount += 1

        if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
            print('   *** Getting next page ...')
            l_request = l_responseData['paging']['next']
            l_response = performRequest(l_request)

            l_responseData = json.loads(l_response)
        else:
            break

def getComments(p_id, p_pageId, p_depth):
    l_depthPadding = ' ' * ((p_depth + 2) * 3)
    # get list of posts in this page's feed
    l_request = 'https://graph.facebook.com/v2.6/{0}/comments?limit={2}&access_token={1}'.format(
        p_id, g_FBToken, G_LIMIT)
    # print('   l_request:', l_request)
    l_response = performRequest(l_request)

    l_responseData = json.loads(l_response)
    # print('   Paging:', l_responseData['paging'])
    print('{0}comment count -->'.format(l_depthPadding[:-3]), len(l_responseData['data']))
    if len(l_responseData['data']) > 0:
        print('{0}Latest date:'.format(l_depthPadding), l_responseData['data'][0]['created_time'])

    while True:
        for l_comment in l_responseData['data']:
            l_commentId = l_comment['id']
            l_commentDate = l_comment['created_time']
            print('{0}--------------------------------------------------------'.format(l_depthPadding))
            print('{0}id      :'.format(l_depthPadding), l_commentId)
            print('{0}date    :'.format(l_depthPadding), l_commentDate)

            l_userId= ''
            if 'from' in l_comment.keys():
                l_userId, l_userIdShort = getOptionalField(l_comment['from'], 'id')
                l_userName, l_userNameShort = getOptionalField(l_comment['from'], 'name')

                print('{0}from    : {1} [{2}]'.format(l_depthPadding, l_userNameShort, l_userId))

                # store user data
                storeUser(l_userId, l_userName, l_commentDate, l_depthPadding)

            l_story, l_storyShort = getOptionalField(l_comment, 'story')
            l_message, l_messageShort = getOptionalField(l_comment, 'message')

            print('{0}story   :'.format(l_depthPadding), l_storyShort)
            print('{0}message :'.format(l_depthPadding), l_messageShort)

            # store post information
            storeObject(l_depthPadding, 'Comm',
                        l_commentId, p_id, p_pageId, l_commentDate, l_story, l_message, p_userId=l_userId)

            # get comments
            getComments(l_commentId, p_pageId, p_depth+1)

        if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
            print('{0}*** Getting next page ...'.format(l_depthPadding))
            l_request = l_responseData['paging']['next']
            l_response = performRequest(l_request)

            l_responseData = json.loads(l_response)
        else:
            break

# calls Facebook's HTTP API and traps errors if any
def performRequest(p_request):
    global g_FBToken

    l_request = p_request

    l_finished = False
    l_response = None

    l_errCount = 0
    while not l_finished:
        try:
            l_response = urllib.request.urlopen(l_request, timeout=10).read().decode('utf-8').strip()
            l_finished = True

        except urllib.error.HTTPError as e:
            l_headersDict = dict(e.headers.items())

            printAndSave('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}\n{10} {11}\n{12} {13}\n'.format(
                'l_errCount     :', l_errCount,
                'Request Problem:', repr(e),
                '   Code        :', e.code,
                '   Errno       :', e.errno,
                '   Headers     :', l_headersDict,
                '   Message     :', e.msg,
                'p_request      :', p_request
            ))

            # Facebook error
            if 'WWW-Authenticate' in l_headersDict.keys():
                l_FBMessage = l_headersDict['WWW-Authenticate']

                # Request limit reached
                if re.search(r'\(#17\) User request limit reached', l_FBMessage):
                    l_wait = G_WAIT_FB
                    printAndSave('{0} {1}\n{2}\n'.format(
                        'FB request limit msg: ', l_FBMessage,
                        'Waiting for {0} seconds'.format(l_wait)
                    ))

                    time.sleep(l_wait)
                    l_request = renewTokenAndRequest(l_request)

                # Session expired
                elif re.search(r'Session has expired', l_FBMessage):
                    l_wait = G_WAIT_FB_SESSION
                    printAndSave('{0} {1}\n{2}\n'.format(
                        'FB session expiry msg: ', l_FBMessage,
                        'Waiting for {0} seconds'.format(l_wait)
                    ))

                    time.sleep(l_wait)
                    l_request = renewTokenAndRequest(l_request)

                # Other FB error
                else:
                    l_wait = getWait(l_errCount)
                    printAndSave('{0} {1}\n{2}\n'.format(
                        'FB msg: ', l_FBMessage,
                        'Waiting for {0} seconds'.format(l_wait)
                    ))

                    time.sleep(l_wait)
                    if l_wait > 60 * 15:
                        l_request = renewTokenAndRequest(l_request)

            # Non FB HTTPError
            else:
                l_wait = getWait(l_errCount)
                printAndSave('Waiting for {0} seconds'.format(l_wait))

                time.sleep(l_wait)
                if l_wait > 60 * 15:
                    l_request = renewTokenAndRequest(l_request)

            l_errCount += 1

        except urllib.error.URLError as e:
            printAndSave('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}\n'.format(
                'l_errCount     :', l_errCount,
                'Request Problem:', repr(e),
                '   Errno       :', e.errno,
                '   Message     :', e.reason,
                'p_request      :', p_request
            ))

            time.sleep(1)

            l_errCount += 1

        except Exception as e:
            printAndSave('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n'.format(
                'l_errCount     :', l_errCount,
                'Request Problem:', repr(e),
                '   Message     :', e.args,
                'p_request      :', p_request
            ))

            time.sleep(1)

            l_errCount += 1

    return l_response

def printAndSave(s):
    print(s, end='')
    g_errFile.write(s)

def getWait(p_errorCount):
    if p_errorCount < 3:
        return 5
    elif p_errorCount < 6:
        return 30
    elif p_errorCount < 9:
        return 60 * 2
    elif p_errorCount < 12:
        return 60 * 5
    elif p_errorCount < 15:
        return 60 * 15
    elif p_errorCount < 18:
        return 60 * 30
    elif p_errorCount < 21:
        return 60 * 60
    else:
        print('Too many errors')
        sys.exit()

def renewTokenAndRequest(p_request):
    l_oldToken = g_FBToken
    getFBToken()
    return re.sub('access_token={0}'.format(l_oldToken),
                  'access_token={0}'.format(g_FBToken), p_request)

def getFBToken():
    global g_FBToken

    l_driver, l_accessToken = loginAs(g_user, g_pass)
    if l_accessToken is not None:
        g_FBToken = l_accessToken
        l_driver.quit()
    else:
        print('Cannot obtain FB Token for:', g_user)
        sys.exit()

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Bulk facebook download of posts/comments                   |')
    print('|                                                            |')
    print('| v. 1.0 - 22/04/2016                                        |')
    print('+------------------------------------------------------------+')

    g_connector = mysql.connector.connect(
        user='root',
        password='TNScrape',
        host='localhost',
        database='FBWatch')

    getFBToken()

    g_errFile = open('FBWatchHTTPErrors.txt', 'w')

    print('l_accessToken:', g_FBToken)

    # list of likes from john.braekernell@yahoo.com --> starting point
    l_request = 'https://graph.facebook.com/v2.6/me/likes?access_token={0}'.format(g_FBToken)
    l_response = performRequest(l_request)

    print('l_request:', l_request)

    # each like is a page
    l_responseData = json.loads(l_response)
    l_finished = False
    while not l_finished:
        for l_liked in l_responseData['data']:

            l_pageId = l_liked['id']
            l_pageName = l_liked['name']
            print('id   :', l_pageId)
            print('name :', l_pageName)

            # store page information
            storeObject('', 'Page', l_pageId, '', '', '', l_pageName, '')

            # get posts from the page
            getPostsFromPage(l_pageId)

        if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
            l_request = l_responseData['paging']['next']
            l_response = performRequest(l_request)

            l_responseData = json.loads(l_response)
        else:
            l_finished = True

    g_connector.close()