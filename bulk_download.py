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
import argparse

import psycopg2

from login_as import loginAs

# ---------------------------------------------------- Globals ---------------------------------------------------------
G_MAX_POST = 500                            # max number of posts retrieved from a page
G_DAYS_DEPTH = 14                           # max number of days a post will be updated after its creation
G_LIKES_DEPTH = 8                           # number of days after which the detailed liked list of a post will be fetched
G_LIMIT = 100                               # number of elements retrieved in one request (API param)
G_WAIT_FB = 60 * 60                         # wait period after a request limit hit (in seconds)

g_connector = None                          # MySQL connector

g_objectStoreAttempts = 0                   # number of times an object store has been attempted
g_objectStored = 0                          # number of objects actually stored
g_postRetrieved = 0
g_commentRetrieved = 0

# obtain from 'Facebook for Developpers --> Tools & Support --> Access Token Tool --> Debug --> Extend Access Token
g_LTToken = 'EAAWW0i6eRkUBAB8LbAiz5paFQCT8hdZA1JSlrNZCZCehuDL7lILiZClhHJRT1gqzdPsZCZBJq5MtOv7qBSvZCFpqmZBdo9JyuxtM72NZBspDoYXO82u6h4BJGMcqUyiu4WJtY3jJ7vZBEYiyKsOvUHU8SZAGJQj4DaZBZCxsZD'
g_LTTokenExpiry = datetime.datetime.strptime('01/08/2016', '%d/%m/%Y')
g_useLTToken = False
g_FBToken = None                            # current FB access token

g_user = 'kabir.eridu@gmail.com'            # user name
g_pass = '12Alhamdulillah'                  # password

g_errFile = None                            # log file for errors

g_FBRequestCount = 0                        # number of requests performed
G_TOKEN_LIFESPAN = 2000                     # number of requests after which the token must be renewed

G_API_VERSION = 'v2.6'                      # version of the FB API used

g_verbose = True                            # True --> maximum progress info

# ---------------------------------------------------- Functions -------------------------------------------------------
def cleanForInsert(s):
    r = re.sub("'", "''", s)
    # r = re.sub(r'\\', r'\\\\', r)

    return r

def storeObject(p_padding, p_type, p_date,
                p_id, p_parentId, p_pageId, p_postId,
                p_FBType, p_shareCount, p_likeCount,
                p_name='',
                p_caption='',
                p_desc='',
                p_story='',
                p_message='',
                p_link='',
                p_picture='',
                p_place='',
                p_source='',
                p_userId='',
                p_raw=''):

    global g_objectStored
    global g_objectStoreAttempts

    g_objectStoreAttempts += 1

    l_stored = False

    # date format: 2016-04-22T12:03:06+0000 ---> 2016-04-22 12:03:06
    l_date = re.sub('T', ' ', p_date)
    l_date = re.sub(r'\+\d+$', '', l_date).strip()

    if len(l_date) == 0:
        l_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    l_cursor = g_connector.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_OBJ"(
            "ID"
            ,"ID_FATHER"
            ,"ID_PAGE"
            ,"ID_POST"
            ,"DT_CRE"
            ,"ST_TYPE"
            ,"ST_FB_TYPE"
            ,"TX_NAME"
            ,"TX_CAPTION"
            ,"TX_DESCRIPTION"
            ,"TX_STORY"
            ,"TX_MESSAGE"
            ,"ID_USER"
            ,"N_LIKES"
            ,"N_SHARES"
            ,"TX_PLACE")
        VALUES(
            '{0}', '{1}', '{2}',  '{3}',  '{4}',  '{5}', '{6}', '{7}',
            '{8}', '{9}', '{10}', '{11}', '{12}', {13},  {14},  '{15}' )
    """.format(
        p_id,
        p_parentId,
        p_pageId,
        p_postId,
        l_date,
        p_type,
        p_FBType,
        cleanForInsert(p_name),
        cleanForInsert(p_caption),
        cleanForInsert(p_desc),
        cleanForInsert(p_story),
        cleanForInsert(p_message),
        p_userId,
        p_likeCount,
        p_shareCount,
        cleanForInsert(p_place)
    )

    # print(l_query)

    try:
        l_cursor.execute(l_query)
        g_connector.commit()
        g_objectStored += 1
        l_stored = True
    except psycopg2.IntegrityError as e:
        if g_verbose:
            print('{0}Object already in TB_OBJ'.format(p_padding))
        #print('{0}PostgreSQL: {1}'.format(p_padding, e))
        g_connector.rollback()
    except Exception as e:
        print('TB_OBJ Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    # store media if any
    if len(p_link + p_picture + p_raw + p_source) > 0:
        l_query = """
            INSERT INTO "FBWatch"."TB_MEDIA"("ID_OWNER","TX_URL_LINK","TX_SRC_PICTURE","TX_RAW")
            VALUES('{0}', '{1}', '{2}',  '{3}')
        """.format(
            p_id,
            cleanForInsert(p_link),
            # p_source is for videos, p_picture for images
            cleanForInsert(p_source if len(p_source) > 0 else p_picture) ,
            cleanForInsert(p_raw)
        )

        # print(l_query)

        try:
            l_cursor.execute(l_query)
            g_connector.commit()
            l_stored = True
        except psycopg2.IntegrityError as e:
            if g_verbose:
                print('{0}Object already in TB_MEDIA'.format(p_padding))
            #print('{0}PostgreSQL: {1}'.format(p_padding, e))
            g_connector.rollback()
        except Exception as e:
            print('TB_MEDIA Unknown Exception: {0}'.format(repr(e)))
            print(l_query)
            sys.exit()

    l_cursor.close()

    print('{0}Object counts: {1} attempts / {2} stored / {3} posts retrieved / {4} comments retrieved'.format(
        p_padding, g_objectStoreAttempts, g_objectStored, g_postRetrieved, g_commentRetrieved))

    return l_stored

def updateObject(p_id, p_shareCount, p_likeCount, p_name, p_caption, p_desc, p_story, p_message):
    l_stored = False

    l_cursor = g_connector.cursor()

    l_query = """
        UPDATE "FBWatch"."TB_OBJ"
        SET
            "N_LIKES" = {1}
            ,"N_SHARES" = {2}
            ,"TX_NAME" = '{3}'
            ,"TX_CAPTION" = '{4}'
            ,"TX_DESCRIPTION" = '{5}'
            ,"TX_STORY" = '{6}'
            ,"TX_MESSAGE" = '{7}'
            ,"DT_LAST_UPDATE" = CURRENT_TIMESTAMP
        WHERE "ID" = '{0}'
    """.format(
        p_id,
        p_likeCount,
        p_shareCount,
        cleanForInsert(p_name),
        cleanForInsert(p_caption),
        cleanForInsert(p_desc),
        cleanForInsert(p_story),
        cleanForInsert(p_message)
    )

    # print(l_query)

    try:
        l_cursor.execute(l_query)
        g_connector.commit()
        l_stored = True
    except psycopg2.IntegrityError as e:
        print('Object Cannot be updated')
        #print('PostgreSQL: {0}'.format(e))
        g_connector.rollback()
    except Exception as e:
        print('TB_OBJ Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

    return l_stored

def storeUser(p_id, p_name, p_date, p_padding):
    # date format: 2016-04-22T12:03:06+0000 ---> 2016-04-22 12:03:06
    l_date = re.sub('T', ' ', p_date)
    l_date = re.sub(r'\+\d+$', '', l_date)

    l_cursor = g_connector.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_USER"("ID", "ST_NAME", "DT_CRE", "DT_MSG")
        VALUES( '{0}', '{1}', '{2}', '{3}' )
    """.format(
        p_id,
        cleanForInsert(p_name),
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        l_date
    )

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connector.commit()
    except psycopg2.IntegrityError as e:
        if g_verbose:
            print('{0}User already known'.format(p_padding))
        #print('{0}PostgreSQL: {1}'.format(p_padding, e))
        g_connector.rollback()
    except Exception as e:
        print('TB_USER Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def getUserInternalId(p_id):
    l_cursor = g_connector.cursor()

    l_retId = None
    l_query = """
        select "ID_INTERNAL"
        from "FBWatch"."TB_USER"
        where "ID" =  '{0}'
    """.format(p_id)

    # print(l_query)
    try:
        l_cursor.execute(l_query)

        for l_internalId, in l_cursor:
            l_retId = l_internalId

    except Exception as e:
        print('TB_USER Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

    return l_retId

def creatLikeLink(p_userIdInternal, p_objIdInternal, p_date):
    # date format: 2016-04-22T12:03:06+0000 ---> 2016-04-22 12:03:06
    l_date = re.sub('T', ' ', p_date)
    l_date = re.sub(r'\+\d+$', '', l_date)

    l_cursor = g_connector.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_LIKE"("ID_USER_INTERNAL","ID_OBJ_INTERNAL","DT_CRE")
        VALUES( '{0}', '{1}', '{2}' )
    """.format(
        p_userIdInternal,
        p_objIdInternal,
        l_date
    )

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connector.commit()
    except psycopg2.IntegrityError as e:
        if g_verbose:
            print('Like link already exists')
        #print('PostgreSQL: {0}'.format(e))
        g_connector.rollback()
    except Exception as e:
        print('TB_LIKE Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def logCommDnl(p_objId, p_fatherId, p_type, p_name):
    l_cursor = g_connector.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_COMM_DNL"("ID_OBJ","ID_FATHER","DT_CRE","ST_TYPE","TX_NAME")
        VALUES( '{0}', '{1}', CURRENT_TIMESTAMP, '{2}', '{3}' )
    """.format(
        p_objId,
        p_fatherId,
        p_type,
        cleanForInsert(p_name)
    )

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connector.commit()
    except psycopg2.IntegrityError as e:
        if g_verbose:
            print('Like link already exists')
        #print('PostgreSQL: {0}'.format(e))
        g_connector.rollback()
    except Exception as e:
        print('TB_LIKE Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def setLikeFlag(p_id):
    l_cursor = g_connector.cursor()

    l_query = """
        update "FBWatch"."TB_OBJ"
        set "F_LIKE_DETAIL" = 'X'
        where "ID" = '{0}'
    """.format(p_id)

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connector.commit()
    except Exception as e:
        print('TB_OBJ Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def purgeDnlComm():
    l_cursor = g_connector.cursor()

    l_query = """
        delete from "FBWatch"."TB_COMM_DNL"
    """

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connector.commit()
    except Exception as e:
        print('TB_COMM_DNL Unknown Exception: {0}'.format(repr(e)))
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

def getPages():
    # purgeDnlComm()

    if g_useLTToken:
        l_cursor = g_connector.cursor()

        l_query = """
            select
                "ID", "TX_NAME"
            from "FBWatch"."TB_OBJ"
            where
                "ST_TYPE" = 'Page'
        """.format(G_DAYS_DEPTH)
        # print(l_query)

        try:
            l_cursor.execute(l_query)

            for l_pageId, l_pageName in l_cursor:
                print('+++ Page:', l_pageName, '+++')
                getPostsFromPage(l_pageId)

        except Exception as e:
            print('Post Update Unknown Exception: {0}'.format(repr(e)))
            print(l_query)
            sys.exit()

        l_cursor.close()
    else:
        # list of likes from user --> starting point
        l_request = 'https://graph.facebook.com/{0}/me/likes?access_token={1}'.format(
            G_API_VERSION, g_FBToken)
        l_response = performRequest(l_request)

        #print('l_request:', l_request)

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
                storeObject(
                    p_padding='',
                    p_type='Page',
                    p_FBType='Page',
                    p_id=l_pageId,
                    p_parentId='',
                    p_pageId='',
                    p_postId='',
                    p_date='',
                    p_likeCount=0,
                    p_shareCount=0,
                    p_name=l_pageName
                )

                # get posts from the page
                getPostsFromPage(l_pageId)

            if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
                l_request = l_responseData['paging']['next']
                l_response = performRequest(l_request)

                l_responseData = json.loads(l_response)
            else:
                l_finished = True

def getPostsFromPage(p_id):
    global g_postRetrieved
    # get list of posts in this page's feed

    l_fieldList = 'id,created_time,from,story,message,' + \
                  'caption,description,icon,link,name,object_id,picture,place,shares,source,type'

    l_request = ('https://graph.facebook.com/{0}/{1}/feed?limit={2}&' +
                 'access_token={3}&fields={4}').format(
        G_API_VERSION, p_id, G_LIMIT, g_FBToken, l_fieldList)

    # print('   l_request:', l_request)
    l_response = performRequest(l_request)

    l_responseData = json.loads(l_response)
    # print('   Paging:', l_responseData['paging'])
    if len(l_responseData['data']) > 0:
        print('   Latest date:', l_responseData['data'][0]['created_time'])

    l_postCount = 0
    l_finished = False
    while not l_finished:
        for l_post in l_responseData['data']:
            g_postRetrieved += 1

            l_postId = l_post['id']
            l_postDate = l_post['created_time']
            l_type = l_post['type']
            l_shares = int(l_post['shares']['count']) if 'shares' in l_post.keys() else 0
            print('   =====[ {0} ]======================================================'.format(l_postCount))
            print('   id          :', l_postId)
            print('   date        :', l_postDate)

            # 2016-04-22T12:03:06+0000
            l_msgDate = datetime.datetime.strptime(
                re.sub(r'\+\d+$', '', l_postDate), '%Y-%m-%dT%H:%M:%S')
            print('   date (P):', l_msgDate)

            # if message older than G_DAYS_DEPTH days ---> break loop
            if (l_msgDate - datetime.datetime.now()).days > G_DAYS_DEPTH:
                print('Post too old')
                l_finished = True
                break

            l_userId = ''
            if 'from' in l_post.keys():
                l_userId, l_userIdShort = getOptionalField(l_post['from'], 'id')
                l_userName, l_userNameShort = getOptionalField(l_post['from'], 'name')

                if g_verbose:
                    print('   from    : {0} [{1}]'.format(l_userNameShort, l_userId))

                # store user data
                storeUser(l_userId, l_userName, l_postDate, '   ')

            l_name, l_nameShort             = getOptionalField(l_post, 'name')
            l_caption, l_captionShort       = getOptionalField(l_post, 'caption')
            l_description, l_descriptionSh  = getOptionalField(l_post, 'description')
            l_story, l_storyShort           = getOptionalField(l_post, 'story')
            l_message, l_messageShort       = getOptionalField(l_post, 'message')

            l_link, x       = getOptionalField(l_post, 'link')
            l_object_id, x  = getOptionalField(l_post, 'object_id')
            l_picture, x    = getOptionalField(l_post, 'picture')
            l_source, x     = getOptionalField(l_post, 'source')

            l_place = ''
            if 'place' in l_post.keys():
                l_place = json.dumps(l_post['place'])

            print('   name        :', l_nameShort)
            if g_verbose:
                print('   caption     :', l_captionShort)
                print('   description :', l_descriptionSh)
                print('   story       :', l_storyShort)
                print('   message     :', l_messageShort)
                print('   link        :', l_link)
                print('   object_id   :', l_object_id)
                print('   picture     :', l_picture)
                print('   place       :', l_place)
                print('   source      :', l_source)
                print('   type        :', l_type)
                print('   shares      :', l_shares)

            # store post information
            if storeObject(
                    p_padding       ='   ',
                    p_type          ='Post',
                    p_FBType        =l_type,
                    p_id            =l_postId,
                    p_parentId      =p_id,
                    p_pageId        =p_id,
                    p_postId        ='',
                    p_date          =l_postDate,
                    p_likeCount     =0,
                    p_shareCount    =l_shares,
                    p_name          =l_name,
                    p_caption       =l_caption,
                    p_desc          =l_description,
                    p_story         =l_story,
                    p_message       =l_message,
                    p_link          =l_link,
                    p_picture       =l_picture,
                    p_place         =l_place,
                    p_source        =l_source,
                    p_userId        =l_userId,
                    p_raw           =json.dumps(l_post['attachment']) if 'attachment' in l_post.keys() else ''
                ):
                # get comments
                #logCommDnl(l_postId, p_id, 'Post', l_name)
                getComments(l_postId, l_postId, p_id, 0)
            else:
                # if already in DB ---> break loop
                print('Page Already done today')
                l_finished = True
                break

            l_postCount += 1

        if l_postCount > G_MAX_POST:
            l_finished = True
        else:
            if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
                print('   *** Getting next page ...')
                l_request = l_responseData['paging']['next']
                l_response = performRequest(l_request)

                l_responseData = json.loads(l_response)
            else:
                break

def getComments(p_id, p_postId, p_pageId, p_depth):
    global g_commentRetrieved

    l_depthPadding = ' ' * ((p_depth + 2) * 3)

    # get list of posts in this page's feed
    l_fieldList = 'id,created_time,from,story,message,user_likes,like_count,comment_count,attachment,object'

    l_request = ('https://graph.facebook.com/{0}/{1}/comments?limit={2}&' +
                 'access_token={3}&fields={4}').format(
        G_API_VERSION, p_id, G_LIMIT, g_FBToken, l_fieldList)
    # print('   l_request:', l_request)
    l_response = performRequest(l_request)

    l_responseData = json.loads(l_response)
    # print('   Paging:', l_responseData['paging'])
    if len(l_responseData['data']) > 0:
        print('{0}Latest date:'.format(l_depthPadding), l_responseData['data'][0]['created_time'])

    l_commCount = 0
    while True:
        for l_comment in l_responseData['data']:
            g_commentRetrieved += 1

            l_commentId = l_comment['id']
            l_commentDate = l_comment['created_time']
            l_commentLikes = int(l_comment['like_count'])
            l_commentCCount = int(l_comment['comment_count'])
            if g_verbose:
                print('{0}--------------------------------------------------------'.format(l_depthPadding))
                print('{0}id      :'.format(l_depthPadding), l_commentId)
                print('{0}date    :'.format(l_depthPadding), l_commentDate)
                print('{0}likes   :'.format(l_depthPadding), l_commentLikes)
                print('{0}sub com.:'.format(l_depthPadding), l_commentCCount)

            l_userId= ''
            if 'from' in l_comment.keys():
                l_userId, l_userIdShort = getOptionalField(l_comment['from'], 'id')
                l_userName, l_userNameShort = getOptionalField(l_comment['from'], 'name')

                if g_verbose:
                    print('{0}from    : {1} [{2}]'.format(l_depthPadding, l_userNameShort, l_userId))

                # store user data
                storeUser(l_userId, l_userName, l_commentDate, l_depthPadding)

            l_story, l_storyShort = getOptionalField(l_comment, 'story')
            l_message, l_messageShort = getOptionalField(l_comment, 'message')

            if g_verbose:
                print('{0}story   :'.format(l_depthPadding), l_storyShort)
                print('{0}message :'.format(l_depthPadding), l_messageShort)

            l_src = ''
            l_url = ''
            l_desc = ''
            l_title = ''
            if 'attachment' in l_comment.keys():
                if 'media' in l_comment['attachment'].keys() and \
                    'image' in l_comment['attachment']['media'].keys() and \
                    'src' in l_comment['attachment']['media']['image'].keys():
                    l_src = l_comment['attachment']['media']['image']['src']

                if 'url' in l_comment['attachment'].keys():
                    l_url = l_comment['attachment']['url']
                if 'title' in l_comment['attachment'].keys():
                    l_title = l_comment['attachment']['title']
                if 'description' in l_comment['attachment'].keys():
                    l_desc = l_comment['attachment']['description']

            if g_verbose:
                print('{0}url     :'.format(l_depthPadding), l_url)
                print('{0}src     :'.format(l_depthPadding), l_src)

            # store comment information
            storeObject(
                p_padding       =l_depthPadding,
                p_type          ='Comm',
                p_FBType        ='Comment',
                p_id            =l_commentId,
                p_parentId      =p_id,
                p_pageId        =p_pageId,
                p_postId        =p_postId,
                p_date          =l_commentDate,
                p_likeCount     =l_commentLikes,
                p_shareCount    =0,
                p_name          ='',
                p_caption       =l_title,
                p_desc          =l_desc,
                p_story         =l_story,
                p_message       =l_message,
                p_link          =l_url,
                p_picture       =l_src,
                p_place         ='',
                p_source        ='',
                p_userId        =l_userId,
                p_raw=json.dumps(l_comment['attachment']) if 'attachment' in l_comment.keys() else ''
            )
            l_commCount += 1

            # get comments
            if l_commentCCount > 0:
                #logCommDnl(l_commentId, p_id, 'Comm', l_messageShort)
                getComments(l_commentId, p_postId, p_pageId, p_depth+1)

        if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
            print('{0}[{1}] *** Getting next page ...'.format(l_depthPadding, l_commCount))
            l_request = l_responseData['paging']['next']
            l_response = performRequest(l_request)

            l_responseData = json.loads(l_response)
        else:
            break

    print('{0}comment download count -->'.format(l_depthPadding[:-3]), l_commCount)

def updatePosts():
    global g_postRetrieved

    # purgeDnlComm()

    l_cursor = g_connector.cursor()

    # All posts not older than G_DAYS_DEPTH days and not already updated in the last day
    # Among these, comments to be downloaded only for those which were not created today
    # ("DT_LAST_UPDATE" not null)
    l_query = """
        select
            "ID"
            , "ID_PAGE"
            , case when "DT_LAST_UPDATE" is null then '' else 'X' end "COMMENT_DOWNLOAD"
        from "FBWatch"."TB_OBJ"
        where
            "ST_TYPE" = 'Post'
            and DATE_PART('day', now()::date - "DT_CRE") <= {0}
            and (
                "DT_LAST_UPDATE" is null
                or DATE_PART('day', now()::date - "DT_LAST_UPDATE") >= 2
            )
    """.format(G_DAYS_DEPTH)
    # print(l_query)

    try:
        l_cursor.execute(l_query)

        for l_postId, l_pageId, l_commentFlag in l_cursor:
            g_postRetrieved += 1
            # get post data
            l_fieldList = 'id,created_time,from,story,message,' + \
                          'caption,description,icon,link,name,object_id,picture,place,shares,source,type'

            l_request = ('https://graph.facebook.com/{0}/{1}?limit={2}&' +
                         'access_token={3}&fields={4}').format(
                G_API_VERSION, l_postId, G_LIMIT, g_FBToken, l_fieldList)
            # print('   l_request:', l_request)
            l_response = performRequest(l_request)

            l_responseData = json.loads(l_response)
            l_shares = int(l_responseData['shares']['count']) if 'shares' in l_responseData.keys() else 0
            print('============= UPDATE ==============================================')
            print('Post ID     :', l_postId)
            if 'created_time' in l_responseData.keys():
                print('Post date   :', l_responseData['created_time'])
            print('Comm. dnl ? :', l_commentFlag)

            l_name, l_nameShort             = getOptionalField(l_responseData, 'name')
            l_caption, l_captionShort       = getOptionalField(l_responseData, 'caption')
            l_description, l_descriptionSh  = getOptionalField(l_responseData, 'description')
            l_story, l_storyShort           = getOptionalField(l_responseData, 'story')
            l_message, l_messageShort       = getOptionalField(l_responseData, 'message')

            print('name        :', l_nameShort)
            if g_verbose:
                print('caption     :', l_captionShort)
                print('description :', l_descriptionSh)
                print('story       :', l_storyShort)
                print('message     :', l_messageShort)
                print('shares      :', l_shares)

            # get post likes
            l_request = ('https://graph.facebook.com/{0}/{1}/likes?limit={2}&' +
                         'access_token={3}&summary=true').format(
                G_API_VERSION, l_postId, 25, g_FBToken, l_fieldList)
            # print('   l_request:', l_request)
            l_response = performRequest(l_request)

            l_responseData = json.loads(l_response)
            l_likeCount = 0
            if 'summary' in l_responseData.keys():
                l_likeCount = int(l_responseData['summary']['total_count'])
            if g_verbose:
                print('likes       :', l_likeCount)

            if updateObject(l_postId, l_shares, l_likeCount, l_name, l_caption, l_description, l_story, l_message)\
                    and l_commentFlag == 'X':
                #logCommDnl(l_postId, l_pageId, 'Post', l_name)
                getComments(l_postId, l_postId, l_pageId, 0)

    except Exception as e:
        print('Post Update Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def getLikesDetail():
    # Count the number of objects affected
    l_query = """
        SELECT
            count(1) AS "LCOUNT"
        FROM
            "FBWatch"."TB_OBJ"
        WHERE
            "ST_TYPE" != 'Page'
            AND DATE_PART('day', now()::date - "DT_CRE") >= {0}
            AND "F_LIKE_DETAIL" is null
    """.format(G_LIKES_DEPTH)

    l_totalCount = 0
    l_cursor = g_connector.cursor()
    try:
        l_cursor.execute(l_query)

        for l_count, in l_cursor:
            l_totalCount = l_count
    except Exception as e:
        print('Likes detail download (count) Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()
    l_cursor = g_connector.cursor()

    # all non page objects older than G_LIKES_DEPTH days and not already processed
    l_query = """
        SELECT
            "ID", "ID_INTERNAL", "DT_CRE"
        FROM
            "FBWatch"."TB_OBJ"
        WHERE
            "ST_TYPE" != 'Page'
            AND DATE_PART('day', now()::date - "DT_CRE") >= {0}
            AND "F_LIKE_DETAIL" is null
    """.format(G_LIKES_DEPTH)
    # print(l_query)

    l_objCount = 0
    try:
        l_cursor.execute(l_query)

        for l_id, l_internalId, l_dtMsg in l_cursor:
            print('{0}/{1}'.format(l_objCount, l_totalCount), l_id, '--->')
            # get post data

            l_request = ('https://graph.facebook.com/{0}/{1}/likes?limit={2}&' +
                         'access_token={3}').format(
                G_API_VERSION, l_id, G_LIMIT, g_FBToken)
            # print('   l_request:', l_request)
            l_response = performRequest(l_request)

            l_responseData = json.loads(l_response)
            l_likeCount = 0
            while True:
                for l_liker in l_responseData['data']:
                    l_likerId = l_liker['id']
                    l_likerName = l_liker['name']

                    l_dtMsgStr = l_dtMsg.strftime('%Y-%m-%dT%H:%M:%S+000')

                    storeUser(l_likerId, l_likerName, l_dtMsgStr, '')

                    l_likerInternalId = getUserInternalId(l_likerId)

                    creatLikeLink(l_likerInternalId, l_internalId, l_dtMsgStr)

                    if g_verbose:
                        print('   {0}/{1} [{2} | {3}] {4}'.format(
                            l_objCount, l_totalCount, l_likerId, l_likerInternalId, l_likerName))

                    l_likeCount += 1

                if 'paging' in l_responseData.keys() and 'next' in l_responseData['paging'].keys():
                    print('   *** {0}/{1} Getting next page ...'.format(l_objCount, l_totalCount))
                    l_request = l_responseData['paging']['next']
                    l_response = performRequest(l_request)

                    l_responseData = json.loads(l_response)
                else:
                    break

            setLikeFlag(l_id)
            print('   {0}/{1} --> {2} Likes:'.format(l_objCount, l_totalCount, l_likeCount))
            l_objCount += 1

    except Exception as e:
        print('Likes detail download Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

# calls Facebook's HTTP API and traps errors if any
def performRequest(p_request):
    global g_FBToken
    global g_FBRequestCount

    l_request = p_request

    l_finished = False
    l_response = None

    # print('g_FBRequestCount:', g_FBRequestCount)

    # replace access token with the latest (this is necessary because
    # some old tokens may remain in the 'next' parameters kept from previous requests)
    l_request = freshenToken(l_request)

    # request new token every G_TOKEN_LIFESPAN API requests
    if g_FBRequestCount > 0 and g_FBRequestCount % G_TOKEN_LIFESPAN == 0:
        l_request = renewTokenAndRequest(l_request)

    g_FBRequestCount += 1

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

                # Request limit reached --> wait G_WAIT_FB s and retry
                if re.search(r'\(#17\) User request limit reached', l_FBMessage):
                    l_wait = G_WAIT_FB
                    printAndSave('{0} {1}\n{2}\n'.format(
                        'FB request limit msg: ', l_FBMessage,
                        'Waiting for {0} seconds'.format(l_wait)
                    ))

                    l_sleepPeriod = 5 * 60
                    for i in range(int(l_wait / l_sleepPeriod)):
                        time.sleep(l_sleepPeriod)
                        l_request = renewTokenAndRequest(l_request)

                # Unknown FB error --> wait 10 s and retry 3 times max then return empty result
                if re.search(r'An unexpected error has occurred', l_FBMessage)\
                        or re.search(r'An unknown error has occurred', l_FBMessage):
                    if l_errCount < 3:
                        l_wait = 10
                        printAndSave('{0} {1}\n{2}\n'.format(
                            'FB unknown error: ', l_FBMessage,
                            'Waiting for {0} seconds'.format(l_wait)
                        ))

                        time.sleep(l_wait)
                        l_request = renewTokenAndRequest(l_request)
                    else:
                        l_response = '{"data": []}'

                        printAndSave('{0} {1}\n{2}\n'.format(
                            'FB unknown error: ', l_FBMessage,
                            'Returned: {0}'.format(l_response)
                        ))

                        l_finished = True

                # Session expired ---> nothing to do
                elif re.search(r'Session has expired', l_FBMessage):
                    printAndSave('{0} {1}\n'.format(
                        'FB session expiry msg: ', l_FBMessage))

                    sys.exit()

                # Unsupported get request ---> return empty data and abandon request attempt
                elif re.search(r'Unsupported get request', l_FBMessage):
                    l_response = '{"data": []}'

                    printAndSave('{0} {1}\n{2}\n'.format(
                        'FB unsupported get msg: ', l_FBMessage,
                        'Returned: {0}'.format(l_response)
                    ))

                    l_finished = True

                # Other FB error
                else:
                    printAndSave('{0} {1}\n'.format(
                        'FB msg: ', l_FBMessage
                    ))

                    sys.exit()

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
    g_errFile.flush()

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

def freshenToken(p_request):
    # case where the token is not at the end of the param string
    l_request = re.sub('access_token=[^&]&',
                       'access_token={0}&'.format(g_FBToken), p_request)
    # case where the token is at the end of the param string
    return re.sub('access_token=[^&]$',
                       'access_token={0}'.format(g_FBToken), l_request)

def renewTokenAndRequest(p_request):
    getFBToken()
    return freshenToken(p_request)

def getFBToken():
    global g_FBToken

    if g_useLTToken:
        g_FBToken = g_LTToken
    else:
        l_driver, l_accessToken = loginAs(g_user, g_pass)
        if l_accessToken is not None:
            printAndSave('g_FBToken before: {0}\n'.format(g_FBToken))
            g_FBToken = l_accessToken
            printAndSave('g_FBToken new   : {0}\n'.format(g_FBToken))
            l_driver.quit()
        else:
            print('Cannot obtain FB Token for:', g_user)
            sys.exit()

# Calls a "what is my Ip" web service to get own IP
def getOwnIp():
    # http://icanhazip.com/
    l_myIp = None
    try:
        l_myIp = urllib.request.urlopen('http://icanhazip.com/').read().decode('utf-8').strip()
    except urllib.error.URLError as e:
        print('Cannot Open Own IP service:', repr(e))

    return l_myIp

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Bulk facebook download of posts/comments                   |')
    print('|                                                            |')
    print('| v. 2.5 - 02/06/2016                                        |')
    print('| ---> migrated to PostgreSQL                                |')
    print('+------------------------------------------------------------+')

    l_parser = argparse.ArgumentParser(description='Download FB data.')
    l_parser.add_argument('--NoPages', help='Do not perform primary download', action='store_true')
    l_parser.add_argument('--NoUpdate', help='Do not perform object update', action='store_true')
    l_parser.add_argument('--NoLikes', help='Do not perform likes detail donwload', action='store_true')
    l_parser.add_argument('--LTToken', help='Use FB long term token', action='store_true')
    l_parser.add_argument('-q', help='Quiet: less progress info', action='store_true')

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.NoPages = False
            self.NoUpdate = False
            self.NoLikes = False
            self.LTToken = False
            self.q = False

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    if c.NoPages: print('Will not perform primary download')
    if c.NoUpdate: print('Will not perform object update')
    if c.NoLikes: print('Will not perform likes detail download')

    if c.LTToken:
        print('Expiry date:', g_LTTokenExpiry.strftime('%A %d %B %Y'))
        if datetime.datetime.now() >= g_LTTokenExpiry:
            print('FB LT Token has expired')
            sys.exit()
        else:
            print('Using Facebook Long Term Token:', g_LTToken, sep='\n')
            g_useLTToken = True

    if c.q:
        g_verbose = False

    # make sure that VPN is off
    l_ownIp = getOwnIp()
    print('l_ownIp:', l_ownIp)
    if l_ownIp != '88.182.132.226':
        print('VPN ?')
        sys.exit()

    g_errFile = open('FBWatchHTTPErrors.txt', 'w')

    # sql_mode='NO_ENGINE_SUBSTITUTION' because of new Utf8 controls in 16.04 MySQL
    g_connector = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    getFBToken()

    # get all post/comments from the liked pages of the queried user
    if not c.NoPages:
        print('*** GET PAGES')
        getPages()

    # refresh posts not older than 8 days and not already updated in the past day
    if not c.NoUpdate:
        print('*** GET UPDATES')
        updatePosts()

    if not c.NoLikes:
        print('*** GET LIKES')
        getLikesDetail()

    g_connector.close()