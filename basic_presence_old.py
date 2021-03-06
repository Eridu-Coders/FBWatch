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
import subprocess
import fcntl
import locale
import psutil
import datetime
import shutil
import gc
import objgraph

from pympler import summary, muppy

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX

from login_as import loginAs
from openvpn import switchonVpn, getOwnIp

from collections import namedtuple

# psutil installation:
# sudo apt-get install python3-dev
# sudo pip3 install psutil

# to get access to a newly installed PostgreSQL server
# http://www.postgresql.org/message-id/4D958A35.8030501@hogranch.com
# $ sudo -u postgres psql

# postgres=> alter user postgres password 'apassword';
# ---------------------------------------------------- Globals ---------------------------------------------------------
# globals for the Phantom ID and password + the Selenium browser driver
# These are necessary to allow periodic refresh of the driver in likeOrComment()
g_phantomId = None
g_phantomPwd = None
g_driver = None

g_browserActions = 0

G_WAIT_FB_MIN = 30
G_WAIT_FB_MAX = G_WAIT_FB_MIN + 60

g_connectorRead = None
g_connectorWrite = None

# number of rows kept by the likes and comment distribution main queries
G_LIMIT_LIKES = 180                     # But only one in 3 will be actually liked
G_LIMIT_COMM = 150                      # But only one in 5 will be actually commented

g_verbose = True

G_DIRTY_FILE = '__Local_DB_is_dirty.txt'

g_locChildPid = None
g_ctpRead = None
g_ptcWrite = None

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

def makeNonBlocking(p_reader):
    fd = p_reader.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

def likeOrComment(p_idPost, p_message=''):
    global g_locChildPid
    global g_driver

    global g_ctpRead
    global g_ptcWrite

    if g_verbose: print('likeOrComment:', p_idPost, p_message)

    l_myMem = getMemUsage(os.getpid())

    if g_locChildPid == None:
        # parent to child
        l_ptcRead, g_ptcWrite = os.pipe()
        l_ptcRead, g_ptcWrite = os.fdopen(l_ptcRead, 'r'), os.fdopen(g_ptcWrite, 'w')

        # child to parent
        g_ctpRead, l_ctpWrite = os.pipe()
        g_ctpRead, l_ctpWrite = os.fdopen(g_ctpRead, 'r'), os.fdopen(l_ctpWrite, 'w')

        makeNonBlocking(g_ctpRead)
        #makeNonBlocking(l_ptcRead)

        g_locChildPid = os.fork()
        if g_locChildPid: # Parent
            l_ctpWrite.close()
            l_ptcRead.close()
            print('Child PID:', g_locChildPid)
        else: # Child
            g_ctpRead.close()
            g_ptcWrite.close()

            # main child loop
            while True:
                l_cmd = l_ptcRead.readline().strip()
                if g_verbose: print('parent sent: ' + l_cmd)

                # end command --> close browser and terminate child
                if l_cmd == 'END':
                    if g_driver is not None:
                        g_driver.close()
                    sys.exit()

                # execution of a like/comment command
                l_extract = re.search('([^§]+)§(.*)', l_cmd)
                if l_extract:
                    l_id = l_extract.group(1)
                    l_msg = l_extract.group(2)
                    if g_verbose: print('l_id:', l_id)
                    if g_verbose: print('l_msg:', l_msg)

                    l_retVal = likeOrCommentExecute(l_id, l_msg)

                    #gobbleMem()

                    if l_retVal:
                        l_ctpWrite.write('FINISHED OK')
                    else:
                        l_ctpWrite.write('FINISHED NOK')
                    l_ctpWrite.flush()

    # here, we are necessarily in the parent because the child exits above
    # and there is a child process running
    l_myMem2 = getMemUsage(os.getpid())

    # send the like/comment command
    g_ptcWrite.write('{0}§{1}\n'.format(p_idPost, p_message))
    g_ptcWrite.flush()
    l_memLogFile = 'mem_log.csv'
    l_retVal = False
    with open(l_memLogFile, 'w') as l_fLog:
        l_fLog.write('"CHILD";"AVAILABLE";"MYSELF"\n')
        while 1:
            l_data = g_ctpRead.readline().strip()
            # good case: the child terminated properly and sent FINISHED
            l_match = re.search('FINISHED\s+(OK|NOK)', l_data)
            if l_match:
                l_retCode = l_match.group(1)
                print('\nChild send end signal - stop monitoring:', l_retCode)
                l_retVal = (l_retCode == 'OK')
                break

            l_childMem = getMemUsage(g_locChildPid)
            l_availableMem = psutil.virtual_memory().available
            l_myMem = getMemUsage(os.getpid())
            print('Mem : {0} child / {1} available / {2} myself'.format(
                  locale.format('%d', int(l_childMem), grouping=True),
                  locale.format('%d', l_availableMem, grouping=True),
                  locale.format('%d', int(l_myMem), grouping=True)),
                  end='\r')
            l_fLog.write('{0};{1};{2}\n'.format(l_childMem, l_availableMem, l_myMem))
            l_fLog.flush()

            # grrrrr
            if l_myMem > 500 * (1024 ** 2):
                print('\nOh my God, I am fat!')
                l_myMem3 = getMemUsage(os.getpid())
                if g_verbose: print('Mem increase child setup      :',
                                    locale.format('%d', int(l_myMem2 - l_myMem), grouping=True))
                if g_verbose: print('Mem increase child monitoring :',
                                    locale.format('%d', int(l_myMem3 - l_myMem2), grouping=True))
                l_quit = input('Finished? ')
                childEnd()
                sys.exit()

            # bad case: the child's memory went over 1Gb --> kill it
            if l_childMem > 1024 ** 3 or l_availableMem < 1024 ** 3:
                print('\nKilling Child process and firefox')
                subprocess.Popen(['sudo', 'kill', '-9', str(g_locChildPid)])

                for l_pid in getPid('firefox'):
                    subprocess.Popen(['sudo', 'kill', '-9', str(l_pid)])

                # close log file and save it
                l_memLogFileSave = \
                    re.sub('.csv', datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S_%f') + '.csv', l_memLogFile)
                shutil.copyfile(l_memLogFile, l_memLogFileSave)

                # globals RAZ
                g_ptcWrite = None
                g_ctpRead = None
                g_locChildPid = None

                break

            # loop 10 times / second
            time.sleep(.1)

    l_myMem3 = getMemUsage(os.getpid())

    randomWait(G_WAIT_FB_MIN, G_WAIT_FB_MAX)

    l_myMem4 = getMemUsage(os.getpid())

    if g_verbose: print('Mem increase child setup      :',
                        locale.format('%d', int(l_myMem2 - l_myMem), grouping=True))
    if g_verbose: print('Mem increase child monitoring :',
                        locale.format('%d', int(l_myMem3 - l_myMem2), grouping=True))
    if g_verbose: print('Mem increase waiting          :',
                        locale.format('%d', int(l_myMem4 - l_myMem3), grouping=True))

    if g_verbose: print('likeOrComment Complete')

    return l_retVal

def gobbleMem():
    t = []
    while True:
        for i in range(10000000):
            t += ['toto']
        time.sleep(.1)

def getPid(p_name):
    try:
        l_rawPidof = subprocess.check_output(["pidof", p_name])
    except subprocess.CalledProcessError as e:
        print('WARNING - pidof return error code:', e.returncode)
        print('pidof output:', e.output)
        return []

    return map(int, l_rawPidof.split())

def childEnd():
    global g_ptcWrite
    global g_ctpRead
    global g_locChildPid

    if g_ptcWrite is not None:
        g_ptcWrite.write('END\n')
        g_ptcWrite.flush()

        # globals RAZ
        g_ptcWrite = None
        g_locChildPid = None
        g_ctpRead = None

def getMemUsage(p_pid):
    l_scale = {'kB': 1024.0, 'mB': 1024.0 * 1024.0, 'KB': 1024.0, 'MB': 1024.0 * 1024.0}

    with open('/proc/{0}/status'.format(p_pid), 'r') as f:
        l_match = re.search('VmSize:\s+(\d+)\s+(\w\w)\n', f.read())
        if l_match:
            return float(l_match.group(1)) * l_scale[l_match.group(2)]

    return 0.0

def likeOrCommentExecute(p_idPost, p_message=''):
    global g_browserActions
    global g_driver

    # opens browser driver and reopen a new one every 20 actions
    if g_driver is None or g_browserActions % 20 == 0:
        # close driver if open
        if g_driver is not None: g_driver.close()

        if g_verbose: print('Opening Selenium Firefox driver and log in')
        # open a new driver
        g_driver = loginAs(g_phantomId, g_phantomPwd, p_api=False)

    l_url = 'http://www.facebook.com/{0}'.format(p_idPost)
    print('\nget:', l_url)
    g_driver.get(l_url)

    # ufi_highlighted_comment
    try:
        if g_verbose: print('\nStart waiting for ufi_highlighted_comment')
        l_commBlock = WebDriverWait(g_driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="ufi_highlighted_comment"]')))

        if g_verbose: print('\nFound ufi_highlighted_comment')
        time.sleep(1)
        if len(p_message) == 0:
            if g_verbose: print('\nStart waiting for UFILikeLink')
            l_likeLink = WebDriverWait(g_driver, 15).until(
                EC.presence_of_element_located(
                        (By.XPATH,
                        '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')
                    )
                )

            if g_verbose: print('\nFound UFILikeLink')
            l_countLoop = 0
            l_retVal = True
            while l_likeLink.text != 'Unlike' and l_likeLink.text != 'Je n’aime plus':
                l_likeLink.click()
                if g_verbose: print('\nUFILikeLink clicked')
                time.sleep(.5)
                l_likeLink = g_driver.find_element_by_xpath(
                    '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')

                if l_countLoop > 10:
                    l_retVal = False
                    if g_verbose: print('\nBroke loop because count > 10')
                    break
                else:
                    l_countLoop += 1

            if g_verbose:
                print('\nLiked {0} -->'.format(p_idPost), re.sub('\s+', ' ', l_commBlock.text).strip())
        else:
            # UFIAddCommentInput _1osb _5yk1
            if g_verbose: print('\nStart waiting for ufi_reply_composer')
            l_commentZone = WebDriverWait(g_driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                    '//div[@data-testid="ufi_reply_composer"]')
                )
            )
            if g_verbose: print('\nFound ufi_reply_composer')

            time.sleep(.5)
            l_commentZone.send_keys(re.sub('\s+', ' ', p_message).strip() + '\n')
            if g_verbose: print('\nMessage sent')

            l_retVal = True
            if g_verbose:
                l_commBlock = g_driver.find_element_by_xpath('//div[@data-testid="ufi_highlighted_comment"]')
                print('\n{0} -->'.format(p_idPost),
                      re.sub('\s+', ' ', l_commBlock.text).strip(),
                      '-->', p_message)

    except EX.TimeoutException:
        print('\nDid not find highlighted comment block or like link')
        l_retVal = False
    except EX.WebDriverException as e:
        print('\nUnknown WebDriverException -->', e)
        if len(p_message) == 0:
            l_likeLink = g_driver.find_element_by_xpath(
                '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')
            if l_likeLink.text == 'Unlike' or l_likeLink.text == 'Je n’aime plus':
                l_retVal = True
            else: l_retVal = False
        else:
            l_retVal = False

    g_browserActions += 1

    return l_retVal

def logOneLike(p_userId, p_objId, p_phantom):
    if g_verbose: print('Logging like:', p_userId, p_objId, p_phantom)
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

    l_cursor.close()

def logOneComment(p_userId, p_objId, p_comm, p_phantom):
    if g_verbose: print('Logging Comment:', p_userId, p_objId, p_phantom, p_comm)
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

    l_cursor.close()

def logOneRiver(p_idPage, p_idPost, p_link, p_phantom):
    l_cursor = g_connectorWrite.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_PRESENCE_RIVERS"("ID_PAGE", "ID_POST", "ST_LINK", "DT_COMM", "ID_PHANTOM")
        VALUES( '{0}', '{1}', '{2}', CURRENT_TIMESTAMP, '{3}' )
    """.format(
        p_idPage, p_idPost, cleanForInsert(p_link), p_phantom)

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connectorWrite.commit()
        markLocalDBasDirty()
    except psycopg2.IntegrityError as e:
        print('WARNING: cannot insert into TB_PRESENCE_RIVERS')
        print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()

    l_cursor.close()

def distributeLikes():
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
    """.format(G_LIMIT_LIKES)

    l_cursor.execute(l_query)

    l_listLikes = []
    for l_idUser, l_userName, l_commId, l_commTxt in l_cursor:
        # only one in 3
        if random.randint(0, 2) == 0:
            l_listLikes += [(l_idUser, l_userName, l_commId, l_commTxt)]

    l_cursor.close()

    l_count = 0
    for l_idUser, l_userName, l_commId, l_commTxt in l_listLikes:
        if len(l_commTxt) > 50:
            l_commTxt = l_commTxt[0:50] + '...'

        print('L <{4:<3}/{5:<3}> [{0:<20}] {1:<30} --> [{2:<40}] {3}'.format(
            l_idUser, l_userName, l_commId, l_commTxt, l_count, len(l_listLikes)))

        l_myMem = getMemUsage(os.getpid())
        if likeOrComment(l_commId):
            l_myMem2 = getMemUsage(os.getpid())
            logOneLike(l_idUser, l_commId, g_phantomId)
        else:
            l_myMem2 = getMemUsage(os.getpid())
            logOneLike(l_idUser, l_commId, '<Dead>')
        l_myMem3 = getMemUsage(os.getpid())

        if g_verbose: print('Mem increase likeOrComment:',
                            locale.format('%d', int(l_myMem2 - l_myMem), grouping=True))
        if g_verbose: print('Mem increase logOneLike   :',
                            locale.format('%d', int(l_myMem3 - l_myMem2), grouping=True))

        if g_verbose: print('Like done:', l_count)
        l_count += 1

    print('+++ Likes Distribution Complete +++')

def distributeComments():
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
    """.format(G_LIMIT_COMM)

    l_cursor.execute(l_query)

    l_listComm = []
    for l_idUser, l_userName, l_commId, l_commTxt in l_cursor:
        # only one in 5 is perfomed
        if random.randint(0, 4) == 0:
            l_listComm += [(l_idUser, l_userName, l_commId, l_commTxt)]

    l_cursor.close()

    l_count = 0
    for l_idUser, l_userName, l_commId, l_commTxt in l_listComm:
        if len(l_commTxt) > 50:
            l_commTxt = l_commTxt[0:50] + '...'

        l_commentNew = genComment()

        print('K <{4:<3}/{6:<3}> [{0:<20}] {1:<30} --> [{2:<40}] {3} --> {5}'.format(
            l_idUser, l_userName, l_commId, l_commTxt, l_count, l_commentNew, len(l_listComm)))

        l_myMem = getMemUsage(os.getpid())
        if likeOrComment(l_commId, l_commentNew):
            l_myMem2 = getMemUsage(os.getpid())
            logOneComment(l_idUser, l_commId, l_commentNew, g_phantomId)
        else:
            l_myMem2 = getMemUsage(os.getpid())
            logOneComment(l_idUser, l_commId, '', '<Dead>')
        l_myMem3 = getMemUsage(os.getpid())

        if g_verbose: print('Mem increase likeOrComment:',
                            locale.format('%d', int(l_myMem2 - l_myMem), grouping=True))
        if g_verbose: print('Mem increase logOneComment:',
                            locale.format('%d', int(l_myMem3 - l_myMem2), grouping=True))

        if g_verbose: print('Comment done:', l_count)
        l_count += 1

    print('*** Comments Distribution Complete ***')

def distributeRivers(p_driver, p_phantom):
    print('*** Rivers Collective Image Distribution ***')
    l_cursor = g_connectorRead.cursor()

    l_query = """
        select
            "Z"."ID_PAGE" "ID_PAGE"
            ,"O"."ID" "ID_POST"
            ,"O"."ST_FB_TYPE"
            ,"O"."ID_USER"
            ,"O"."TX_MESSAGE"
            ,"O"."DT_CRE"
        from
            "FBWatch"."TB_OBJ" "O" join (
                select
                    "J"."ID_PAGE" as "ID_PAGE"
                    , max("J"."DT_CRE") "DLATEST"
                from
                    "FBWatch"."TB_OBJ" "J"
                where
                    "J"."ST_TYPE" = 'Post'
                    and ("ID_USER" = "ID_PAGE" or length("ID_USER") = 0)
                group by "J"."ID_PAGE"
            ) "Z" on "Z"."ID_PAGE" = "O"."ID_PAGE" and "Z"."DLATEST" = "O"."DT_CRE"
            left outer join "FBWatch"."TB_PRESENCE_RIVERS" "X" on "X"."ID_POST" = "O"."ID"
        where
            "O"."ST_TYPE" = 'Post'
            and "X"."ID_POST" is null
    """

    try:
        l_cursor.execute(l_query)

        l_count = 0
        for l_idPage, l_idPost, l_fbType, l_id_user, l_message, l_dtPost in l_cursor:
            if len(l_message) > 50:
                l_message = l_message[0:50] + '...'

            l_newLink = genRiversLink()

            print('{0:<3} [{1:<20}/{2:<20}] {3:<30} --> [{4}]'.format(
                l_count, l_idPage, l_idPost, l_message, l_newLink))

            if likeOrComment(l_idPost, l_newLink):
                logOneRiver(l_idPage, l_idPost, l_newLink, g_phantomId)
            else:
                logOneRiver(l_idPage, l_idPost, '', '<Dead>')

            l_count += 1

    except Exception as e:
        print('Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

def genRiversLink():
    l_link = random.choice([
        'https://www.facebook.com/photo.php?fbid=121863904894315&set=pcb.121955864885119',
        'https://www.facebook.com/photo.php?fbid=121868288227210&set=pb.100012121181501.-2207520000.1463124971.',
        'https://www.facebook.com/photo.php?fbid=121867988227240&set=pb.100012121181501.-2207520000.1463124971.',
        'https://www.facebook.com/photo.php?fbid=121867858227253&set=pb.100012121181501.-2207520000.1463124971.',
        'https://www.facebook.com/photo.php?fbid=121867331560639&set=pb.100012121181501.-2207520000.1463124971.',
        'https://www.facebook.com/photo.php?fbid=121865154894190&set=pb.100012121181501.-2207520000.1463124971.'
    ])

    return l_link


g_commList = [
    'Indeed', 'Ok', 'That sounds right', 'I agree', '100% agree',
    'Quite right', 'Absolutely right', 'Hell yes', 'Right on the mark', 'Yes indeed',
    'Yes', 'True', 'So true', 'Yeah', 'Hell Yeah', 'Fuck Yeah', 'Thumbs up man',
    "Can't say anything against that", "Couldn't agree more",
    'There is no denying it', 'The Truth always comes out',
    "Couldn't have said it better myself", 'You are right', 'You are so right',
    'Damn right', 'Spot on', 'You are damn right', 'Sure enough']

g_choiceCommList = None

def genComment():
    global g_commList
    global g_choiceCommList

    if g_choiceCommList is None:
        l_commPunct = \
            [c + '.' for c in g_commList] + \
            [c + '!' for c in g_commList] + \
            [c + '!!' for c in g_commList]

        l_compoList = []
        for i in range(len(l_commPunct)):
            for j in range(len(l_commPunct)):
                if i != j:
                    l_compoList += [l_commPunct[i] + ' ' + l_commPunct[j]]

        g_choiceCommList = l_compoList + \
                           g_commList + [c + '!' for c in g_commList] + [c + '!!' for c in g_commList]

    l_commentNew = random.choice(g_choiceCommList)

    if random.randint(0, 19) == 10:
        l_index = random.randint(0, len(l_commentNew)-1)
        l_cnList = list(l_commentNew)
        l_cnList[l_index] = g_transChar[l_cnList[l_index]]
        l_commentNew = ''.join(l_cnList)

    if random.randint(0, 19) >= 10:
        l_commentNew = re.sub(r'\.$', '', l_commentNew)

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

def sendBackTable(p_table, p_dateField):
    l_cursor = g_connectorRead.cursor()

    l_query = ''
    try:
        l_query = """
            select * from "FBWatch"."{0}"
            where "{1}" > (
                select min("DT_LIKE")
                from "FBWatch"."TB_PRESENCE_LIKE"
                where "ID_PHANTOM" = '[Cache]'
            )
        """.format(p_table, p_dateField)
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

    # only write here (into the local DB). Reading from the main DB is done with pg_dump for speed's sake
    g_connectorWrite = psycopg2.connect(
        host='localhost',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    l_tableList = ['TB_PHANTOM', 'TB_PRESENCE_COMM', 'TB_PRESENCE_LIKE',
                   'TB_USER_AGGREGATE', 'TB_OBJ']
    for l_table in l_tableList:
        print('+++ Dropping', l_table)
        performQuery('drop table if exists "FBWatch"."{0}"'.format(l_table))


    for l_table in l_tableList:
        print('+++ Backuping', l_table, 'remotely on main server')
        l_remoteCommand = (r'/usr/bin/pg_dump --host localhost --port 5432 --username "postgres" ' +
                           r'--format custom --verbose ' +
                           r'--file "/home/fi11222/disk-partage/Vrac/{0}.backup" ' +
                           r'--table "\"FBWatch\".\"{0}\"" "FBWatch"').format(l_table)

        executeRemotely(l_remoteCommand)

    for l_table in l_tableList:
        print('+++ Restoring locally:', l_table)
        os.system('/usr/bin/pg_restore --host localhost --port 5432 --username "postgres" ' +
                  '--dbname "FBWatch" --verbose ' +
                  '"/home/fi11222/share-partage/Vrac/{0}.backup"'.format(l_table))

    logOneLike('[Cache]', '[Cache]', '[Cache]')
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

    l_suffixList = ['COMM', 'LIKE']
    for l_suf in l_suffixList:
        l_table = 'TB_PRESENCE_' + l_suf
        l_dtField = 'DT_' + l_suf
        print('Sending', l_table, 'contents back to main server')
        sendBackTable(l_table, l_dtField)

    g_connectorRead.close()
    g_connectorWrite.close()

def executeRemotely(p_command):
    print('Remote command:', p_command)
    p = subprocess.Popen(
        'sshpass -p 15Eyyaka ssh -t -t fi11222@192.168.0.52 {0}'.format(p_command).split(' '),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    l_output, l_err = p.communicate()
    print('+++ stdout:', l_output.decode('utf-8').strip())
    print('+++ stderr:', l_err.decode('utf-8').strip())

def choosePhantom():
    # DB operations Will be executed before VPN cuts us off
    g_connectorRead = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    l_cursor = g_connectorRead.cursor()

    l_query = """
        select * from "FBWatch"."TB_PHANTOM"
    """

    l_phantomList = []
    RecPhantom = namedtuple('RecPhantom', 'PhantomId PhantomPwd PhantomVpn FbUserId')
    try:
        l_cursor.execute(l_query)

        for l_phantomId, l_phantomPwd, l_vpn, l_fbId in l_cursor:
            l_phantomId = l_phantomId.strip()
            l_phantomPwd = l_phantomPwd.strip()

            l_phantomList += [RecPhantom(l_phantomId, l_phantomPwd, l_vpn, l_fbId)]
    except Exception as e:
        print('Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()

    g_connectorRead.close()

    for i in range(len(l_phantomList)):
        l_phantomId = l_phantomList[i].PhantomId
        l_phantomVPN = l_phantomList[i].PhantomVpn

        print('[{0:<2}] {1:<30} --> {2}'.format(i, l_phantomId, l_phantomVPN))

    l_choiceNum = None
    l_finished = False
    while not l_finished:
        l_choice = input('Which one [0 to {0}]: '.format(len(l_phantomList)-1))
        try:
            l_choiceNum = int(l_choice)
        except ValueError:
            print('Not a number')
            continue

        if l_choiceNum < 0 or l_choiceNum >= len(l_phantomList):
            print('Must be between 0 and {0}'.format(len(l_phantomList)))
        else:
            l_finished = True

    l_process = switchonVpn(l_phantomList[l_choiceNum].PhantomVpn, p_verbose=True)
    if l_process is not None:
        l_driver = loginAs(l_phantomList[l_choiceNum].PhantomId, l_phantomList[l_choiceNum].PhantomPwd, p_api=False)
    else:
        print('Cannot connect VPN')
        l_driver = None
    print('IP:', getOwnIp())

    l_quit = input('Finished? ')

    if l_driver is not None:
        l_driver.close()

    if l_process is not None and l_process.poll() is None:
        print('Killing process pid:', l_process.pid)
        # kill the VPN process (-15 = SIGTERM to allow child termination)
        subprocess.Popen(['sudo', 'kill', '-15', str(l_process.pid)])
        print('IP:', getOwnIp())

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Basic facebook presence                                    |')
    print('|                                                            |')
    print('| v. 2.6 - 24/05/2016                                        |')
    print('+------------------------------------------------------------+')

    random.seed()

    locale.setlocale(locale.LC_ALL, '')
    print('Locale: {0}'.format(locale.getlocale()))

    l_parser = argparse.ArgumentParser(description='Download FB data.')
    l_parser.add_argument('-l', help='List phantoms and login as one', action='store_true')
    l_parser.add_argument('-q', help='Quiet: less progress info', action='store_true')
    l_parser.add_argument('--NoLikes', help='Do not perform likes distribution', action='store_true')
    l_parser.add_argument('--NoComments', help='Do not perform comments distribution', action='store_true')
    l_parser.add_argument('--NoCache', help='Do not update local DB cache', action='store_true')
    l_parser.add_argument('--CleanLocal', help='Only cleans up local DB', action='store_true')
    l_parser.add_argument('--Test', help='No VPN and only KA as user', action='store_true')
    l_parser.add_argument('--GenComment', help='Test gen comment', action='store_true')
    l_parser.add_argument('--SshTest', help='Test remote command execution', action='store_true')
    l_parser.add_argument('--LOCTest', help='Test likeOrComment', action='store_true')

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.l = False
            self.q = False
            self.GenComment = False
            self.NoLikes = False
            self.CleanLocal = False
            self.Test = False
            self.SshTest = False
            self.NoCache = False
            self.NoComments = False
            self.LOCTest = False

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    if c.l:
        choosePhantom()
        sys.exit()

    if c.q:
        g_verbose = False

    if c.GenComment:
        for i in range(1000):
            print(i, genComment())
        sys.exit()

    if c.LOCTest:
        g_phantomId = 'kabir.eridu@gmail.com'
        g_phantomPwd = '12Alhamdulillah'
        likeOrComment('10154315425328690_10154326253248690', 'Well ?')
        likeOrComment('10154315425328690_10154326253248690', 'Are you really sure ?')
        childEnd()
        sys.exit()

    if c.SshTest:
        print('ssh test')
        l_remoteCommand = r'/usr/bin/pg_dump --host localhost --port 5432 --username "postgres" ' +\
                          r'--format custom --verbose ' +\
                          r'--file "/home/fi11222/disk-partage/Vrac/TB_PHANTOM.backup" ' +\
                          r'--table "\"FBWatch\".\"TB_PHANTOM\"" "FBWatch"'

        print('Remote command:', l_remoteCommand)
        p = subprocess.Popen(
            'sshpass -p 15Eyyaka ssh -t -t fi11222@192.168.0.52 {0}'.format(l_remoteCommand).split(' '),
             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        l_output, l_err = p.communicate()
        print('+++ stdout:', l_output.decode('utf-8').strip())
        print('+++ stderr:', l_err.decode('utf-8').strip())
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

        if not c.NoCache:
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

    # No exception catching here to allow full stack trace printout

    l_phantomList = []
    RecPhantom = namedtuple('RecPhantom', 'PhantomId PhantomPwd PhantomVpn FbUserId')
    l_cursor.execute(l_query)

    for l_phantomId, l_phantomPwd, l_vpn, l_fbId in l_cursor:
        l_phantomId = l_phantomId.strip()
        l_phantomPwd = l_phantomPwd.strip()

        l_phantomList += [RecPhantom(l_phantomId, l_phantomPwd, l_vpn, l_fbId)]

    l_cursor.close()

    g_connectorRead.close()
    g_connectorWrite.close()

    for l_phantomId, l_phantomPwd, l_vpn, l_fbId in l_phantomList:
        g_phantomId = l_phantomId.strip()
        g_phantomPwd = l_phantomPwd.strip()

        if c.Test:
            # test parameters and no VPN
            g_phantomId = 'kabir.eridu@gmail.com'
            g_phantomPwd = '12Alhamdulillah'
        else:
            l_process = switchonVpn(l_vpn, p_verbose=True)

        # if failure to connect vpn --> next phantom
        if l_process == None: continue

        if c.Test or l_process.poll() is None:
            print('g_phantomId :', g_phantomId)
            print('g_phantomPwd:', g_phantomPwd)

            # no longer necessary because handled inside likeOrComment()
            # g_driver = loginAs(g_phantomId, g_phantomPwd, p_api=False)

            # separate connection for each phantom to avoid any possible interference from vpn
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

            if not c.NoLikes:
                distributeLikes()

            if not c.NoComments:
                distributeComments()

            g_connectorRead.close()
            g_connectorWrite.close()

            # sends signal to child process to end (also closes current firefox Selenium driver in the child)
            childEnd()

        if c.Test:
            # only one user if in test mode --> no need to loop
            break
        elif l_process.poll() is None:
            # kill the VPN process (-15 = SIGTERM to allow child termination)
            print('Stopping VPN')
            subprocess.Popen(['sudo', 'kill', '-15', str(l_process.pid)])
            print('IP:', getOwnIp())
        else:
            print('Big problem!!')
            sys.exit()

    # update main DB with results
    if not c.Test:
        updateMainDB()
        markLocalDBasClean()

