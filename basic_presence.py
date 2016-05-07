#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import psycopg2
import sys
import urllib.request
import urllib.error
import urllib.parse
import time
import random

from login_as import loginAs

# ---------------------------------------------------- Globals ---------------------------------------------------------
G_WAIT_FB_MIN = 20
G_WAIT_FB_MAX = 60

g_connectorRead = None
g_connectorWrite = None

# ---------------------------------------------------- Functions -------------------------------------------------------
# wait random time between given bounds
def randomWait(p_minDelay, p_maxDelay):
    if p_minDelay > 0 and p_maxDelay > p_minDelay:
        l_wait = p_minDelay + (p_maxDelay - p_minDelay)*random.random()
        print('Waiting for {0:.2f} seconds ...'.format(l_wait))
        time.sleep(l_wait)

def likeOnePost(p_idPost, p_token):

    l_request = ('https://graph.facebook.com/v2.6/{0}/' +
                 'likes?access_token={1}').format(p_idPost, p_token)
    try:
        l_response = urllib.request.urlopen(
            l_request,
            data=urllib.parse.urlencode([('toto', 'tutu')]).encode()).read().decode('utf-8').strip()

        print('l_response:', l_response)
        randomWait(G_WAIT_FB_MIN, G_WAIT_FB_MAX)
        return True
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
        return False

def logOneLike(p_userId, p_objId):
    l_cursor = g_connectorWrite.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_PRESENCE_LIKE"("ID_USER", "ID_OBJ", "DT_LIKE")
        VALUES( '{0}', '{1}', CURRENT_TIMESTAMP )
    """.format(
        p_userId, p_objId)

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connectorWrite.commit()
    except psycopg2.IntegrityError as e:
        print('WARNING: cannot insert into TB_PRESENCE_LIKE')
        print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()
    except Exception as e:
        print('TB_PRESENCE_LIKE Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Basic facebook presence                                    |')
    print('|                                                            |')
    print('| v. 1.0 - 07/05/2016                                        |')
    print('+------------------------------------------------------------+')

    random.seed()
    
    l_driver, l_accessToken = loginAs('kabir.eridu@gmail.com', '12Alhamdulillah')
    l_driver.quit()

    # used to read from TB_THEME
    g_connectorRead = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")
    # used to write to TB_WORD_THEME
    g_connectorWrite = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    l_cursor = g_connectorRead.cursor()

    l_query = """
        select
            "Z"."ID" "ID_USER"
            ,"Z"."ST_NAME"
            ,"O"."ID" "ID_OBJ"
            ,"O"."TX_MESSAGE"
        from "FBWatch"."TB_OBJ" "O" join (
            select
                "U"."ID"
                ,"U"."ST_NAME"
                , max("O"."DT_CRE") "DLATEST"
            from
                "FBWatch"."TB_USER_AGGREGATE" "U" join "FBWatch"."TB_OBJ" "O" on "O"."ID_USER" = "U"."ID"
            where "U"."AUTHCOUNT" > 10
            group by "U"."ID"
            order by "U"."TTCOUNT" desc
            limit 200
            ) "Z" on "Z"."ID" = "O"."ID_USER" and "Z"."DLATEST" = "O"."DT_CRE"
    """

    try:
        l_cursor.execute(l_query)

        for l_idUser, l_userName, l_commId, l_commTxt in l_cursor:
            print('[{0:<20}] {1:<30} --> [{2:<40}] {3}'.format(l_idUser, l_userName, l_commId, l_commTxt[0:80]))
            if likeOnePost(l_commId, l_accessToken):
                logOneLike(l_idUser, l_commId)
    except Exception as e:
        print('Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()