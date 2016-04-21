#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import urllib.request
import json
import re

from login_as import loginAs

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Facebook Graph API test                                    |')
    print('|                                                            |')
    print('| v. 1.0 - 21/04/2016                                        |')
    print('+------------------------------------------------------------+')

    # l_driver = loginAs('kabir.eridu@gmail.com', '12Alhamdulillah')
    l_driver, l_accessToken = loginAs('john.braekernell@yahoo.com', '15Eyyaka')
    if l_accessToken is not None:
        print('l_accessToken:', l_accessToken)

        l_request = 'https://graph.facebook.com/v2.6/me/likes?access_token={0}'.format(l_accessToken)
        l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

        print('l_request:', l_request)
        # print('l_response:', l_response)

        l_responseData = json.loads(l_response)
        print('l_responseData:', repr(l_responseData['data']))
        for l_liked in l_responseData['data']:
            print('id   :', l_liked['id'])
            print('name :', l_liked['name'])

            l_request = 'https://graph.facebook.com/v2.6/{0}/feed?access_token={1}'.format(
                l_liked['id'], l_accessToken)
            l_response = urllib.request.urlopen(l_request).read().decode('utf-8').strip()

            print('   l_request:', l_request)
            # print('   l_response:', l_response)

            l_responseData2 = json.loads(l_response)
            for l_post in l_responseData2['data']:
                print('   ------------------------------------------------------')
                print('   id      :', l_post['id'])
                print('   date    :', l_post['created_time'])

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

        l_driver.quit()