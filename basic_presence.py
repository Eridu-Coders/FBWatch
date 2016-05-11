#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import psycopg2
import sys
import time
import random
import re
import argparse

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX

from login_as import loginAs

# ---------------------------------------------------- Globals ---------------------------------------------------------
G_WAIT_FB_MIN = 60
G_WAIT_FB_MAX = 120

g_connectorRead = None
g_connectorWrite = None

G_LIMIT_TOP_USERS = 200

g_verbose = True

# ---------------------------------------------------- Functions -------------------------------------------------------
def cleanForInsert(s):
    r = re.sub("'", "''", s)
    # r = re.sub(r'\\', r'\\\\', r)

    return r

# wait random time between given bounds
def randomWait(p_minDelay, p_maxDelay):
    if p_minDelay > 0 and p_maxDelay > p_minDelay:
        l_wait = p_minDelay + (p_maxDelay - p_minDelay)*random.random()
        print('Waiting for {0:.2f} seconds ...'.format(l_wait))
        time.sleep(l_wait)

def likeOrComment(p_idPost, p_driver, p_message=''):
    p_driver.get('http://www.facebook.com/{0}'.format(p_idPost))

    # ufi_highlighted_comment
    try:
        l_commBlock = WebDriverWait(l_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="ufi_highlighted_comment"]')))

        time.sleep(1)
        if len(p_message) == 0:
            l_likeLink = WebDriverWait(l_driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                    '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')
                )
            )

            l_countLoop = 0
            l_retVal = True
            while l_likeLink.text != 'Unlike':
                l_likeLink.click()
                time.sleep(.5)
                l_likeLink = l_driver.find_element_by_xpath(
                    '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')

                if l_countLoop > 10:
                    l_retVal = False
                    break
                else:
                    l_countLoop += 1

            if g_verbose:
                print('Liked {0} -->'.format(p_idPost), re.sub('\s+', ' ', l_commBlock.text).strip())
        else:
            # UFIAddCommentInput _1osb _5yk1
            l_commentZone = WebDriverWait(l_driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                    '//div[@data-testid="ufi_reply_composer"]')
                )
            )
            l_commentZone.send_keys(re.sub('\s+', ' ', p_message).strip() + '\n')

            l_retVal = True
            if g_verbose:
                print('{0} -->'.format(p_idPost),
                      re.sub('\s+', ' ', l_commBlock.text).strip(),
                      '-->', p_message)
    except EX.TimeoutException:
        print('Did not find highlighted comment block')
        l_retVal = False
    except EX.WebDriverException as e:
        print('Unknown WebDriverException -->', e)
        if len(p_message) == 0:
            l_likeLink = l_driver.find_element_by_xpath(
                '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')
            if l_likeLink.text == 'Unlike':
                l_retVal = True
            else: l_retVal = False
        else:
            l_retVal = False

    randomWait(G_WAIT_FB_MIN, G_WAIT_FB_MAX)
    return l_retVal

def logOneLike(p_userId, p_objId, p_phantom):
    l_cursor = g_connectorWrite.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_PRESENCE_LIKE"("ID_USER", "ID_OBJ", "DT_LIKE", "ID_PHANTOM")
        VALUES( '{0}', '{1}', CURRENT_TIMESTAMP, '{2}' )
    """.format(
        p_userId, p_objId, p_phantom)

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

def logOneComment(p_userId, p_objId, p_comm, p_phantom):
    l_cursor = g_connectorWrite.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_PRESENCE_COMM"("ID_USER", "ID_OBJ", "ST_COMM", "DT_COMM", "ID_PHANTOM")
        VALUES( '{0}', '{1}', '{2}', CURRENT_TIMESTAMP, '{3}' )
    """.format(
        p_userId, p_objId, cleanForInsert(p_comm), p_phantom)

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connectorWrite.commit()
    except psycopg2.IntegrityError as e:
        print('WARNING: cannot insert into TB_PRESENCE_COMM')
        print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()
    except Exception as e:
        print('TB_PRESENCE_COMM Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def distributeLikes(p_driver, p_phantom):
    print('+++ Likes Distribution +++')
    l_cursor = g_connectorRead.cursor()

    l_query = """
        select
            "Z"."ID" "ID_USER"
            ,"Z"."ST_NAME"
            ,"O"."ID" "ID_OBJ"
            ,"O"."TX_MESSAGE"
        from
            "FBWatch"."TB_OBJ" "O" join (
                select
                    "U"."ID"
                    ,"U"."ST_NAME"
                    ,"U"."TTCOUNT"
                    , max("J"."DT_CRE") "DLATEST"
                from
                    "FBWatch"."TB_USER_AGGREGATE" "U" join "FBWatch"."TB_OBJ" "J" on "J"."ID_USER" = "U"."ID"
                where
                    "U"."AUTHCOUNT" > 10
                    and "J"."ST_FB_TYPE" = 'Comment'
                    and length("J"."TX_MESSAGE") > 50
                group by "U"."ID"
            ) "Z" on "Z"."ID" = "O"."ID_USER" and "Z"."DLATEST" = "O"."DT_CRE"
            left outer join "FBWatch"."TB_PRESENCE_LIKE" "X" on "X"."ID_OBJ" = "O"."ID"
        where
            "X"."ID_OBJ" is null
        order by "Z"."TTCOUNT" desc
        limit {0}
    """.format(G_LIMIT_TOP_USERS)

    try:
        l_cursor.execute(l_query)

        l_count = 0
        for l_idUser, l_userName, l_commId, l_commTxt in l_cursor:
            if len(l_commTxt) > 50:
                l_commTxt = l_commTxt[0:50] + '...'

            print('{4:<3} [{0:<20}] {1:<30} --> [{2:<40}] {3}'.format(
                l_idUser, l_userName, l_commId, l_commTxt, l_count))

            if likeOrComment(l_commId, p_driver):
                logOneLike(l_idUser, l_commId, p_phantom)
            else:
                logOneLike(l_idUser, l_commId, '<Dead>')

            l_count += 1

    except Exception as e:
        print('Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def distributeComments(p_driver, p_phantom):
    print('*** Comments Distribution ***')
    l_cursor = g_connectorRead.cursor()

    l_query = """
        select
            "Z"."ID" "ID_USER"
            ,"Z"."ST_NAME"
            ,"O"."ID" "ID_OBJ"
            ,"O"."TX_MESSAGE"
        from
            "FBWatch"."TB_OBJ" "O" join (
                select
                    "U"."ID"
                    ,"U"."ST_NAME"
                    ,"U"."TTCOUNT"
                    , max("J"."DT_CRE") "DLATEST"
                from
                    "FBWatch"."TB_USER_AGGREGATE" "U" join "FBWatch"."TB_OBJ" "J" on "J"."ID_USER" = "U"."ID"
                where
                    "U"."AUTHCOUNT" > 10
                    and "J"."ST_FB_TYPE" = 'Comment'
                    and length("J"."TX_MESSAGE") > 100
                group by "U"."ID"
            ) "Z" on "Z"."ID" = "O"."ID_USER" and "Z"."DLATEST" = "O"."DT_CRE"
            left outer join "FBWatch"."TB_PRESENCE_COMM" "X" on "X"."ID_OBJ" = "O"."ID"
        where
            "X"."ID_OBJ" is null
        order by "Z"."TTCOUNT" desc
        limit {0}
    """.format(G_LIMIT_TOP_USERS)

    try:
        l_cursor.execute(l_query)

        l_count = 0
        for l_idUser, l_userName, l_commId, l_commTxt in l_cursor:
            if len(l_commTxt) > 50:
                l_commTxt = l_commTxt[0:50] + '...'

            l_commList = [
                'Indeed', 'Ok', 'Well I guess ...', 'How about that?', 'I agree', '100% agree',
                'Quite right', 'Absolutely right', 'Hell yes!', 'Right on the mark', 'Yes indeed',
                'Yes', 'True', 'So true', 'Yeah', 'Hell Yeah', 'Fuck Yeah', 'Thumbs up man',
                'Can\'t say anything against that', 'Couldn\'t agree more',
                'There is no denying it', 'The Truth always comes out',
                'Couldn\'t have said it better myself', 'You are right', 'You are so right' ]
            l_commentNew = random.choice(l_commList + [c+'!' for c in l_commList] + [c+'!!' for c in l_commList])

            print('{4:<3} [{0:<20}] {1:<30} --> [{2:<40}] {3} --> {5}'.format(
                l_idUser, l_userName, l_commId, l_commTxt, l_count, l_commentNew))

            if likeOrComment(l_commId, p_driver, l_commentNew):
                logOneComment(l_idUser, l_commId, l_commentNew, p_phantom)
            else:
                logOneComment(l_idUser, l_commId, '', '<Dead>')

            l_count += 1

    except Exception as e:
        print('Unknown Exception: {0}'.format(repr(e)))
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
    print('| v. 2.0 - 11/05/2016                                        |')
    print('+------------------------------------------------------------+')

    l_parser = argparse.ArgumentParser(description='Download FB data.')
    l_parser.add_argument('-NoLikes', help='Do not perform likes distribution', action='store_true')
    l_parser.add_argument('-q', help='Quiet: less progress info', action='store_true')

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.NoLikes = False
            self.q = False

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    if c.q:
        g_verbose = False
    random.seed()

    l_phantomId = 'kabir.eridu@gmail.com'
    l_phantomPwd = '12Alhamdulillah'
    l_driver = loginAs(l_phantomId, l_phantomPwd, p_api=False)

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

    if not c.NoLikes:
        distributeLikes(l_driver, l_phantomId)
    distributeComments(l_driver, l_phantomId)

    l_driver.quit()

