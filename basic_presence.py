#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import psycopg2
import sys
import time
import random
import re
import argparse
import os

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX

from login_as import loginAs
from openvpn import switchonVpn

# to get access to a newly installed PostgreSQL server
# http://www.postgresql.org/message-id/4D958A35.8030501@hogranch.com
# $ sudo -u postgres psql

# postgres=> alter user postgres password 'apassword';
# ---------------------------------------------------- Globals ---------------------------------------------------------
G_WAIT_FB_MIN = 30
G_WAIT_FB_MAX = G_WAIT_FB_MIN + 60

g_connectorRead = None
g_connectorWrite = None

G_LIMIT_TOP_USERS = 200

g_verbose = True

G_DIRTY_FILE = '__Local_DB_is_dirty.txt'

g_transChar = {
    'A': 'Z',
    'Z': 'E',
    'E': 'R',
    'R': 'F',
    'T': 'Y',
    'Y': 'H',
    'U': 'T',
    'I': 'K',
    'O': 'L',
    'P': 'O',
    'Q': 'S',
    'S': 'Z',
    'D': 'F',
    'F': 'R',
    'G': 'B',
    'H': 'J',
    'J': 'N',
    'K': 'L',
    'L': 'M',
    'M': 'P',
    'W': 'Q',
    'X': 'W',
    'C': 'D',
    'V': 'B',
    'B': 'N',
    'N': 'J',
    'a': 'q',
    'z': 'e',
    'e': 'z',
    'r': 't',
    't': 'r',
    'y': 'u',
    'u': 'i',
    'i': 'j',
    'o': 'p',
    'p': 'o',
    'q': 'z',
    's': 'q',
    'd': 'q',
    'f': 'r',
    'g': 'h',
    'h': 'b',
    'j': 'u',
    'k': 'l',
    'l': 'm',
    'm': 'p',
    'w': 's',
    'x': 'c',
    'c': 'f',
    'v': 'b',
    'b': 'n',
    'n': 'h',
    '1': '&',
    '0': 'à',
    '%': 'ù',
    '!': '§',
    '.': ',',
    "'": '4',
    ' ': ' '
}

# ---------------------------------------------------- Functions -------------------------------------------------------
def cleanForInsert(s):
    r = re.sub("'", "''", s)
    # r = re.sub(r'\\', r'\\\\', r)

    return r

def markLocalDBasDirty():
    with open(G_DIRTY_FILE, 'w') as f:
        f.write('Hello')
        f.close()

def isLocalDBDirty():
    return os.path.isfile(G_DIRTY_FILE)

def markLocalDBasClean():
    os.remove(G_DIRTY_FILE)

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
                l_commBlock = l_driver.find_element_by_xpath('//div[@data-testid="ufi_highlighted_comment"]')
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
        markLocalDBasDirty()
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
        markLocalDBasDirty()
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

            l_commentNew = genComment()

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

def genComment():
    l_commList = [
        'Indeed', 'Ok', 'That sounds right', 'I agree', '100% agree',
        'Quite right', 'Absolutely right', 'Hell yes', 'Right on the mark', 'Yes indeed',
        'Yes', 'True', 'So true', 'Yeah', 'Hell Yeah', 'Fuck Yeah', 'Thumbs up man',
        "Can't say anything against that", "Couldn't agree more",
        'There is no denying it', 'The Truth always comes out',
        "Couldn't have said it better myself", 'You are right', 'You are so right',
        'Damn right', 'Spot on', 'You are damn right', 'Sure enough']
    l_commPunct = \
        [c + '.' for c in l_commList] + \
        [c + '!' for c in l_commList] + \
        [c + '!!' for c in l_commList]

    l_compoList = []
    for i in range(len(l_commPunct)):
        for j in range(len(l_commPunct)):
            if i != j:
                l_compoList += [l_commPunct[i] + ' ' + l_commPunct[j]]

    l_commentNew = random.choice(l_compoList +
                                 l_commList + [c + '!' for c in l_commList] + [c + '!!' for c in l_commList])

    if random.randint(0, 19) == 10:
        l_index = random.randint(0, len(l_commentNew)-1)
        l_cnList = list(l_commentNew)
        l_cnList[l_index] = g_transChar[l_cnList[l_index]]
        l_commentNew = ''.join(l_cnList)

    return l_commentNew


def performQuery(p_query, p_record=None, p_verbose=True):
    l_cursor = g_connectorWrite.cursor()

    try:
        if p_record is None:
            l_cursor.execute(p_query)
        else:
            l_cursor.execute(p_query, p_record)
        g_connectorWrite.commit()
    except psycopg2.IntegrityError as e:
        if p_verbose:
            print('WARNING: Could not fully execute:\n', p_query)
            print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()
    except Exception as e:
        print('PG Unknown Exception: {0}'.format(repr(e)))
        print('Query  :', p_query)
        print('Record :', p_record)
        sys.exit()

    l_cursor.close()

def slurpTable(p_table):
    l_cursor = g_connectorRead.cursor()

    l_query = ''
    try:
        l_query = 'select * from "FBWatch"."{0}"'.format(p_table)
        l_cursor.execute(l_query)

        for l_record in l_cursor:
            performQuery(
                'insert into "FBWatch"."{0}" values({1})'.format(
                    p_table,
                    ','.join(['%s' for i in range(len(l_record))])),
                l_record,
                p_verbose=False
            )
    except Exception as e:
        print('PG Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def cacheData():
    global g_connectorRead
    global g_connectorWrite

    g_connectorRead = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    g_connectorWrite = psycopg2.connect(
        host='localhost',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    l_tableList = ['TB_PRESENCE_COMM', 'TB_PRESENCE_LIKE', 'TB_USER_AGGREGATE', 'TB_OBJ', 'TB_PHANTOM']
    for l_table in l_tableList:
        print('+++ Dropping', l_table)
        performQuery('drop table if exists "FBWatch"."{0}"'.format(l_table))

    print('+++ Backuping main server')
    os.system('cat /home/fi11222/FBWatch/save_main.sh | sshpass -p 15Eyyaka ssh fi11222@192.168.0.52')

    for l_table in l_tableList:
        print('+++ Restoring locally:', l_table)
        os.system('/usr/bin/pg_restore --host localhost --port 5432 --username "postgres" ' +
                  '--dbname "FBWatch" --verbose ' +
                  '"/home/fi11222/share-partage/Vrac/{0}.backup"'.format(l_table))

    g_connectorRead.close()
    g_connectorWrite.close()

def updateMainDB():
    global g_connectorRead
    global g_connectorWrite

    g_connectorRead = psycopg2.connect(
        host='localhost',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    g_connectorWrite = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    l_tableList = ['TB_PRESENCE_COMM', 'TB_PRESENCE_LIKE']
    for l_table in l_tableList:
        print('Sending', l_table, 'contents back to main server')
        slurpTable(l_table)

    g_connectorRead.close()
    g_connectorWrite.close()

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Basic facebook presence                                    |')
    print('|                                                            |')
    print('| v. 2.1 - 12/05/2016                                        |')
    print('+------------------------------------------------------------+')

    l_parser = argparse.ArgumentParser(description='Download FB data.')
    l_parser.add_argument('-NoLikes', help='Do not perform likes distribution', action='store_true')
    l_parser.add_argument('-q', help='Quiet: less progress info', action='store_true')
    l_parser.add_argument('-CleanLocal', help='Only cleans up local DB', action='store_true')
    l_parser.add_argument('-Test', help='No VPN and only KA as user', action='store_true')
    l_parser.add_argument('-gc', help='Test gen comment', action='store_true')

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.NoLikes = False
            self.q = False
            self.CleanLocal = False
            self.Test = False
            self.gc = False

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    if c.q:
        g_verbose = False

    if c.gc:
        for i in range(1000):
            print(i, genComment())
        sys.exit()

    random.seed()

    if os.geteuid() != 0:
        print('Must be root')
        sys.exit()

    if c.Test:
        # Test set-up --> direct connection
        g_connectorRead = psycopg2.connect(
            host='192.168.0.52',
            database="FBWatch",
            user="postgres",
            password="murugan!")
        g_connectorWrite = psycopg2.connect(
            host='192.168.0.52',
            database="FBWatch",
            user="postgres",
            password="murugan!")
    else:
        # get local copies of tables used here
        if isLocalDBDirty():
            updateMainDB()
            markLocalDBasClean()

        if c.CleanLocal:
            sys.exit()

        cacheData()

        # switch to local DB to avoid being cut off by VPN
        g_connectorRead = psycopg2.connect(
            host='localhost',
            database="FBWatch",
            user="postgres",
            password="murugan!")
        g_connectorWrite = psycopg2.connect(
            host='localhost',
            database="FBWatch",
            user="postgres",
            password="murugan!")

    l_cursor = g_connectorRead.cursor()

    l_query = """
        select * from "FBWatch"."TB_PHANTOM"
    """

    try:
        l_cursor.execute(l_query)

        for l_phantomId, l_phantomPwd, l_vpn in l_cursor:
            if c.Test:
                # test parameters and no VPN
                l_phantomId = 'kabir.eridu@gmail.com'
                l_phantomPwd = '12Alhamdulillah'
            else:
                l_process = switchonVpn(l_vpn, p_verbose=True)

            if c.Test or l_process.poll() is None:
                l_driver = loginAs(l_phantomId, l_phantomPwd, p_api=False)

                if not c.NoLikes:
                    distributeLikes(l_driver, l_phantomId)
                distributeComments(l_driver, l_phantomId)

                l_driver.quit()

            if c.Test:
                # only one user if in test mode --> no need to loop
                break
            elif l_process.poll() is None:
                l_process.kill()

    except Exception as e:
        print('Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

    g_connectorRead.close()
    g_connectorWrite.close()

    # update main DB with results
    if not c.Test:
        updateMainDB()
        markLocalDBasClean()

