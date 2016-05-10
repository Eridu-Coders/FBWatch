#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import urllib.request
import urllib.error
import urllib.parse
import json
import re
import sys

from login_as import loginAs

# ---------------------------------------------------- Functions -------------------------------------------------------
def readTest():
    fOut = open('api_test-fields.txt', 'w')

    l_driver, l_accessToken = loginAs('john.braekernell@yahoo.com', '15Eyyaka')
    if l_accessToken is not None:
        print('l_accessToken:', l_accessToken)

        l_request = 'https://graph.facebook.com/v2.6/me/likes?access_token={0}'.format(l_accessToken)
        l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

        # print('l_request:', l_request)
        # print('l_response:', l_response)

        l_responseData = json.loads(l_response)
        # print('l_responseData:', repr(l_responseData['data']))
        if 'paging' in l_responseData.keys():
            print('paging in likes:', repr(l_responseData['paging']))

        for l_liked in l_responseData['data']:
            print('id     :', l_liked['id'])
            print('name   :', l_liked['name'])

            l_fieldList = 'id,created_time,from,story,message,' + \
                          'caption,description,icon,link,name,object_id,picture,place,shares,source,type'

            l_request = ('https://graph.facebook.com/v2.6/{0}/' +
                         'feed?access_token={1}&fields={2}').format(
                l_liked['id'], l_accessToken, l_fieldList)
            try:
                l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()
            except urllib.error.HTTPError as e:
                l_headersDict = dict(e.headers.items())

                print('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}\n{10} {11}'.format(
                    'Request Problem:', repr(e),
                    '   Code        :', e.code,
                    '   Errno       :', e.errno,
                    '   Headers     :', l_headersDict,
                    '   Message     :', e.msg,
                    'p_request      :', l_request
                ))
                sys.exit()

            # print('l_request:', l_request)
            # print('   l_response:', l_response)

            l_responseData2 = json.loads(l_response)
            if 'paging' in l_responseData2.keys():
                print('paging :', repr(l_responseData2['paging']))

            for l_post in l_responseData2['data']:
                print('   ===========================================================')
                print('   id      :', l_post['id'])
                print('   date    :', l_post['created_time'])

                fOut.write('====================================\n')
                fOut.write('fields P:{0}\n'.format(l_post.keys()))
                for l_field in l_post.keys():
                    fOut.write('   {0}: {1}\n'.format(l_field, l_post[l_field]))

                if 'from' in l_post.keys():
                    print('   from    : {0} [{1}]'.format(l_post['from']['name'], l_post['from']['id']))

                if 'story' in l_post.keys():
                    l_msg = re.sub('\s+', ' ', l_post['story']).strip()
                    if len(l_msg) > 100:
                        l_msg = l_msg[0:100] + ' ... ({0})'.format(len(l_msg))
                    print('   story   :', l_msg)

                if 'message' in l_post.keys():
                    l_msg = re.sub('\s+', ' ', l_post['message']).strip()
                    if len(l_msg) > 100:
                        l_msg = l_msg[0:100] + ' ... ({0})'.format(len(l_msg))
                    print('   message :', l_msg)

                if 'story' not in l_post.keys() and 'message' not in l_post.keys():
                    print('   *** ', repr(l_post))

                l_request = ('https://graph.facebook.com/v2.6/{0}/comments?access_token={1}&' +
                             'fields=id,created_time,from,story,message,' +
                             'user_likes,like_count,comment_count,attachment,object').format(
                    l_post['id'], l_accessToken)
                l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

                # print('   l_request:', l_request)
                # print('   l_response:', l_response)
                l_responseData3 = json.loads(l_response)
                if 'paging' in l_responseData3.keys():
                    print('   paging  :', repr(l_responseData3['paging']))

                for l_comment in l_responseData3['data']:
                    print('      ------------------------------------------------------')
                    print('      id      :', l_comment['id'])
                    print('      date    :', l_comment['created_time'])
                    print('      fields  :', l_comment.keys())

                    fOut.write('fields 1:{0}\n'.format(l_comment.keys()))

                    if 'paging' in l_comment.keys():
                        print('      paging  :', repr(l_comment['paging']))

                    if 'from' in l_comment.keys():
                        print('      from    : {0} [{1}]'.format(
                            l_comment['from']['name'],
                            l_comment['from']['id']))

                    if 'story' in l_comment.keys():
                        l_msg = re.sub('\s+', ' ', l_comment['story']).strip()
                        if len(l_msg) > 100:
                            l_msg = l_msg[0:100] + ' ... ({0})'.format(len(l_msg))
                        print('      story   :', l_msg)

                    if 'message' in l_comment.keys():
                        l_msg = re.sub('\s+', ' ', l_comment['message']).strip()
                        if len(l_msg) > 100:
                            l_msg = l_msg[0:100] + ' ... ({0})'.format(len(l_msg))
                        print('      message :', l_msg)

                    if 'story' not in l_comment.keys() and 'message' not in l_comment.keys():
                        print('      +++ ', repr(l_comment))

                    l_request = ('https://graph.facebook.com/v2.6/{0}' +
                                 '?access_token={1}&fields=user_likes,like_count,comment_count,attachment,object').format(
                        l_comment['id'], l_accessToken)
                    try:
                        l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()
                    except urllib.error.HTTPError as e:
                        l_headersDict = dict(e.headers.items())

                        print('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}\n{10} {11}'.format(
                            'Request Problem:', repr(e),
                            '   Code        :', e.code,
                            '   Errno       :', e.errno,
                            '   Headers     :', l_headersDict,
                            '   Message     :', e.msg,
                            'p_request      :', l_request
                        ))
                        sys.exit()

                    l_responseData4 = json.loads(l_response)
                    print('      fields 2:', l_responseData4.keys())
                    fOut.write('fields 2:{0}\n'.format(l_responseData4.keys()))

                    for l_field in l_responseData4.keys():
                        fOut.write('   {0}: {1}\n'.format(l_field, l_responseData4[l_field]))

                    fOut.flush()

    l_driver.quit()

def postTest():
    l_driver, l_accessToken = loginAs('kabir.eridu@gmail.com', '12Alhamdulillah')
    l_driver.quit()


    l_request = ('https://graph.facebook.com/v2.6/{0}/' +
                 'comments?access_token={1}').format("586860451438994_587077508083955", l_accessToken)
    try:
        l_response = urllib.request.urlopen(
            l_request,
            data=urllib.parse.urlencode([('message', 'All right.')]).encode()).read().decode('utf-8').strip()

        print('l_response:', l_response)
    except urllib.error.HTTPError as e:
        l_headersDict = dict(e.headers.items())

        l_headersRep = '\n'
        for k in l_headersDict.keys():
            l_headersRep += '      [{0:<20}] --> {1}\n'.format(k, l_headersDict[k])

        print('{0} {1}\n{2} {3}\n{4} {5}\n{6} {7}\n{8} {9}\n{10} {11}'.format(
            'Request Problem:', repr(e),
            '   Code        :', e.code,
            '   Errno       :', e.errno,
            '   Headers     :', l_headersRep,
            '   Message     :', e.msg,
            'p_request      :', l_request
        ))
        sys.exit()

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Facebook Graph API test                                    |')
    print('|                                                            |')
    print('| v. 2.0 - 07/05/2016                                        |')
    print('+------------------------------------------------------------+')

    postTest()