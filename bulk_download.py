#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import urllib.request
import json
import re
import time

from login_as import loginAs

# ---------------------------------------------------- Globals ---------------------------------------------------------
G_MAX_POST = 300
G_LIMIT = 100

# ---------------------------------------------------- Functions -------------------------------------------------------
def storeObject(p_id, p_parentId, p_pageId, p_date, p_text1, p_text2):
    pass

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

def getPostsFromPage(p_id, p_accessToken):
    # get list of posts in this page's feed
    l_request = 'https://graph.facebook.com/v2.6/{0}/feed?limit={2}&access_token={1}'.format(
        p_id, p_accessToken, G_LIMIT)
    # print('   l_request:', l_request)
    l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

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

            l_story, l_storyShort = getOptionalField(l_post, 'story')
            l_message, l_messageShort = getOptionalField(l_post, 'message')

            print('   story   :', l_storyShort)
            print('   message :', l_messageShort)

            # store post information
            storeObject(l_postId, p_id, p_id, l_postDate, l_story, l_message)

            l_postCount += 1

        if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
            print('   *** Getting next page ...')
            l_request = l_responseData['paging']['next']
            l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

            l_responseData = json.loads(l_response)
        else:
            break

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Bulk facebook download of posts/comments                   |')
    print('|                                                            |')
    print('| v. 1.0 - 22/04/2016                                        |')
    print('+------------------------------------------------------------+')

    # list of likes from john.braekernell@yahoo.com --> starting point
    l_driver, l_accessToken = loginAs('john.braekernell@yahoo.com', '15Eyyaka')
    if l_accessToken is not None:
        print('l_accessToken:', l_accessToken)

        l_request = 'https://graph.facebook.com/v2.6/me/likes?access_token={0}'.format(l_accessToken)
        l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

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
                storeObject(l_pageId, '', '', '', l_pageName, '')

                # get posts from the page
                getPostsFromPage(l_pageId, l_accessToken)

            if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
                l_request = l_responseData['paging']['next']
                l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

                l_responseData = json.loads(l_response)
            else:
                l_finished = True