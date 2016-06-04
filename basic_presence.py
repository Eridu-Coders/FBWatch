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
import csv
import glob

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

# globals for the Phantom ID and password + the Selenium browser driver
# These are necessary to allow periodic refresh of the driver in likeOrComment()
g_phantomId = None
g_phantomPwd = None
g_browserDriver = None

g_browserActions = 0

G_WAIT_FB_MIN = 20
G_WAIT_FB_MAX = G_WAIT_FB_MIN + 40

g_connectorRead = None
g_connectorWrite = None

# number of rows kept by the likes and comment distribution main queries
G_MAX_FR_PER_DAY = 4
G_LIMIT_LIKES = 240                     # But only one in 3 will be actually liked
G_LIMIT_COMM = 100                      # But only one in 10 will be actually commented
G_LIMIT_FRIEND = 50                     # But only G_MAX_FR_PER_DAY friend requests will be sent

g_verbose = True

g_monitorPid = None

# ---------------------------------------------------- Functions -------------------------------------------------------
def launchMemoryMonitor():
    global g_monitorPid
    print('Launching Memory Monitor')

    l_parentPid = os.getpid()

    g_monitorPid = os.fork()
    if g_monitorPid:  # Parent
        print('Monitor PID:', g_monitorPid)
    else:  # Child
        l_measurementsPerSec = 10
        while True:
            l_csvMonitor = 'mem_monitor.csv'
            with open(l_csvMonitor, 'w') as l_fMonitor:
                l_fMonitor.write('"PID";"TYPE";"DATE";"MEM"\n')

                # 5 min monitoring spans
                for i in range(5 * 60 * l_measurementsPerSec):
                    l_pidCount = 0
                    for l_pid in getPid('basic_presence.py'):
                        l_pidCount += 1
                        l_mem = getMemUsage(l_pid)
                        if l_pid == l_parentPid:
                            l_type = 'P'
                        elif l_pid == os.getpid():
                            l_type = 'M'
                        else:
                            l_type = 'X'
                        l_fMonitor.write('"{0}";"{1}";"{2}";{3}\n'.format(
                            l_pid,
                            l_type,
                            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                            int(l_mem)
                        ))
                        l_fMonitor.flush()

                        # kill all pids if any grows to more than 400 Mb big
                        # or total available mem goes below 1 Gb
                        if l_mem > 400 * (1024 ** 2) or psutil.virtual_memory().available < 1024 ** 3:
                            for l_pid in getPid('basic_presence.py'):
                                if l_pid != os.getpid():
                                    subprocess.Popen(['sudo', 'kill', '-9', str(l_pid)])
                                    l_fMonitor.write('"{0}";;"{1}";{2}\n'.format(
                                        l_pid,
                                        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                                        -1
                                    ))
                                sys.exit()

                    # if the monitoring job is alone --> no point staying there
                    if l_pidCount < 2:
                        sys.exit()

                    # 10 measurements per second
                    time.sleep(1.0 / l_measurementsPerSec)

                l_fMonitor.close()
                # depth of retention = 1 ---> between 5 and 10 minutes data
                shutil.copyfile(l_csvMonitor, re.sub(r'\.csv', '_0.csv', l_csvMonitor))

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

def makeNonBlocking(p_reader):
    fd = p_reader.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

def gobbleMem():
    t = []
    while True:
        for i in range(10000000):
            t += ['toto']
        time.sleep(.1)

def getPid(p_name):
    try:
        l_rawPidof = subprocess.check_output(['pidof', '-x', p_name])
    except subprocess.CalledProcessError as e:
        print('WARNING - pidof return error code:', e.returncode)
        print('pidof output:', e.output)
        return []

    return map(int, l_rawPidof.split())

def getMemUsage(p_pid):
    l_scale = {'kB': 1024.0, 'mB': 1024.0 * 1024.0, 'KB': 1024.0, 'MB': 1024.0 * 1024.0}

    with open('/proc/{0}/status'.format(p_pid), 'r') as f:
        l_match = re.search('VmSize:\s+(\d+)\s+(\w\w)\n', f.read())
        if l_match:
            return float(l_match.group(1)) * l_scale[l_match.group(2)]

    return 0.0

def handleWebDriver():
    global g_browserActions
    global g_browserDriver

    # opens browser driver and reopen a new one every 20 actions
    if g_browserDriver is None or g_browserActions % 20 == 0:
        # close driver if open
        if g_browserDriver is not None: g_browserDriver.close()

        if g_verbose: print('Opening Selenium Firefox driver and log in')
        # open a new driver
        g_browserDriver = loginAs(g_phantomId, g_phantomPwd, p_api=False)

def friendRequest(p_uId):
    global g_browserDriver
    global g_browserActions

    handleWebDriver()

    # go to user's page
    l_url = 'http://www.facebook.com/{0}'.format(p_uId)
    if g_verbose: print('get:', l_url)
    g_browserDriver.get(l_url)

    try:
        if g_verbose: print('Start waiting for friend request button')
        l_friendButton = WebDriverWait(g_browserDriver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@id="u_ps_0_0_0"]//div[@class="FriendButton"]')))

        # enter link into status text area
        if g_verbose: print('Found friend request button')
        time.sleep(.5)

        l_friendButton.click()

        l_retVal = True
    except EX.TimeoutException:
        print('Did not find friend request button')
        l_retVal = False
    except EX.WebDriverException as e:
        print('Unknown WebDriverException -->', e)
        l_retVal = False

    g_browserActions += 1

    return l_retVal

def postRiverLink(p_link):
    global g_browserDriver
    global g_browserActions

    handleWebDriver()

    # go to my own feed
    l_url = 'http://www.facebook.com/'
    if g_verbose: print('get:', l_url)
    g_browserDriver.get(l_url)

    l_step = 0
    try:
        if g_verbose: print('Start waiting for xhpc_message textarea')
        l_textArea = WebDriverWait(g_browserDriver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//textarea[@name="xhpc_message"]')))

        # enter link into status text area
        if g_verbose: print('Found xhpc_message textarea')
        time.sleep(.5)
        l_textArea.send_keys(re.sub('\s+', ' ', p_link).strip())
        if g_verbose: print('Link [{0}] entered'.format(p_link))

        l_step = 1
        # click submit button
        l_button = WebDriverWait(g_browserDriver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="_ohf rfloat"]//button[@type="submit"]')))
        if g_verbose: print('Button Found')
        l_button.click()
        time.sleep(.5)

        # _4d6i img
        l_step = 2
        if g_verbose: print('Waiting for waiting icon to disappear')
        WebDriverWait(g_browserDriver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//img[@class="_4d6i img"]')))

        if g_verbose: print('Link [{0}] posted'.format(p_link))
        l_retVal = True
    except EX.TimeoutException:
        if l_step == 0:
            print('Did not find xhpc_message textarea')
        elif l_step == 0:
            print('Did not find submit button')
        else:
            print('Did not find icon')
        l_retVal = False
    except EX.WebDriverException as e:
        print('Unknown WebDriverException -->', e)
        l_retVal = False

    g_browserActions += 1

    return l_retVal

def likeOrComment(p_idPost, p_message=''):
    global g_browserDriver
    global g_browserActions

    handleWebDriver()

    l_url = 'http://www.facebook.com/{0}'.format(p_idPost)
    if g_verbose: print('get:', l_url)
    g_browserDriver.get(l_url)

    # ufi_highlighted_comment
    try:
        if g_verbose: print('Start waiting for ufi_highlighted_comment')
        l_commBlock = WebDriverWait(g_browserDriver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-testid="ufi_highlighted_comment"]')))

        if g_verbose: print('Found ufi_highlighted_comment')
        time.sleep(1)
        if len(p_message) == 0:
            if g_verbose: print('Start waiting for UFILikeLink')
            l_likeLink = WebDriverWait(g_browserDriver, 15).until(
                EC.presence_of_element_located(
                        (By.XPATH,
                        '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')
                    )
                )

            if g_verbose: print('Found UFILikeLink')
            l_countLoop = 0
            l_retVal = True
            while l_likeLink.text != 'Unlike' and l_likeLink.text != 'Je n’aime plus':
                l_likeLink.click()
                if g_verbose: print('UFILikeLink clicked')
                time.sleep(.5)
                l_likeLink = g_browserDriver.find_element_by_xpath(
                    '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')

                if l_countLoop > 10:
                    l_retVal = False
                    if g_verbose: print('Broke loop because count > 10')
                    break
                else:
                    l_countLoop += 1

            if g_verbose:
                print('Liked {0} -->'.format(p_idPost), re.sub('\s+', ' ', l_commBlock.text).strip())
        else:
            # UFIAddCommentInput _1osb _5yk1
            if g_verbose: print('Start waiting for ufi_reply_composer')
            l_commentZone = WebDriverWait(g_browserDriver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                    '//div[@data-testid="ufi_reply_composer"]')
                )
            )
            if g_verbose: print('Found ufi_reply_composer')

            time.sleep(.5)
            l_commentZone.send_keys(re.sub('\s+', ' ', p_message).strip() + '\n')
            if g_verbose: print('Message sent')

            l_retVal = True
            if g_verbose:
                l_commBlock = g_browserDriver.find_element_by_xpath('//div[@data-testid="ufi_highlighted_comment"]')
                print('{0} -->'.format(p_idPost),
                      re.sub('\s+', ' ', l_commBlock.text).strip(),
                      '-->', p_message)

    except EX.TimeoutException:
        print('Did not find highlighted comment block or like link')
        l_retVal = False
    except EX.WebDriverException as e:
        print('Unknown WebDriverException -->', e)
        if len(p_message) == 0:
            l_likeLink = g_browserDriver.find_element_by_xpath(
                '//div[@data-testid="ufi_highlighted_comment"]//a[@class="UFILikeLink"]')
            if l_likeLink.text == 'Unlike' or l_likeLink.text == 'Je n’aime plus':
                l_retVal = True
            else: l_retVal = False
        else:
            l_retVal = False

    g_browserActions += 1

    return l_retVal

def logOneLike(p_userId, p_objId, p_phantom):
    print('Logging like:', p_userId, p_objId, p_phantom)
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
        print('l_query:', l_query)
        print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()

    l_cursor.close()

def logOneComment(p_userId, p_objId, p_comm, p_phantom):
    print('Logging Comment:', p_userId, p_objId, p_phantom, p_comm)
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
        print('l_query:', l_query)
        print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()

    l_cursor.close()

def logOneRiver(p_link, p_phantom):
    print('Logging River:', p_link, p_phantom)
    l_cursor = g_connectorWrite.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_PRESENCE_RIVERS"("ST_LINK", "DT_COMM", "ID_PHANTOM")
        VALUES( '{0}', CURRENT_TIMESTAMP, '{1}' )
    """.format(
        cleanForInsert(p_link), p_phantom)

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connectorWrite.commit()
    except psycopg2.IntegrityError as e:
        print('WARNING: cannot insert into TB_PRESENCE_RIVERS')
        print('l_query:', l_query)
        print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()

    l_cursor.close()

def logOneFriendRequest(p_uId, p_phantom, p_failed=False):
    print('Logging Friend Request:', p_uId, p_phantom)
    l_cursor = g_connectorWrite.cursor()

    l_query = """
        INSERT INTO "FBWatch"."TB_PRESENCE_FRIEND"("ID_USER", "DT_FRIEND", "ID_PHANTOM", "F_FAIL")
        VALUES( '{0}', CURRENT_TIMESTAMP, '{1}', '{2}' )
    """.format(p_uId, p_phantom, 'X' if p_failed else '')

    # print(l_query)
    try:
        l_cursor.execute(l_query)
        g_connectorWrite.commit()
    except psycopg2.IntegrityError as e:
        print('WARNING: cannot insert into TB_PRESENCE_FRIEND')
        print('l_query:', l_query)
        print('PostgreSQL: {0}'.format(e))
        g_connectorWrite.rollback()

    l_cursor.close()

def prepareLikeActions(p_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId):
    print('+++ Likes Actions +++')
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

    for l_idUser, l_userName, l_commId, l_commTxt in l_cursor:
        # only one in 3
        if random.randint(0, 2) == 0:
            if len(l_commTxt) > 50:
                l_commTxt = l_commTxt[0:50] + '...'

            p_csvWriter.writerow(['LIKE', l_commId, l_idUser, l_userName, l_commTxt, ''])

    l_cursor.close()

def prepareCommActions(p_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId):
    print('*** Comments Actions ***')
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

    for l_idUser, l_userName, l_commId, l_commTxt in l_cursor:
        # only one in 10 is perfomed
        if random.randint(0, 9) == 0:
            if len(l_commTxt) > 50:
                l_commTxt = l_commTxt[0:50] + '...'

            p_csvWriter.writerow(['COMM', l_commId, l_idUser, l_userName, l_commTxt, genComment()])

    l_cursor.close()

def prepareFriendActions(p_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId):
    print('### Friend Request Actions ###')

    # check that the max number of FR has not already been sent
    l_cursor = g_connectorRead.cursor()

    l_dayFRCount = 0
    l_query = """
        select
            "ID_PHANTOM"
            , to_char("DT_FRIEND", 'YYYY-MM-DD') as "DAY"
            , count(1) as "COUNT"
        from "FBWatch"."TB_PRESENCE_FRIEND"
        where
            to_char("DT_FRIEND", 'YYYY-MM-DD') = to_char(current_timestamp, 'YYYY-MM-DD')
            and "ID_PHANTOM" = '{0}'
        group by
            "ID_PHANTOM"
            , to_char("DT_FRIEND", 'YYYY-MM-DD')
        order by to_char("DT_FRIEND", 'YYYY-MM-DD') desc
    """.format(p_phantomId)
    # print(l_query)
    l_cursor.execute(l_query)

    for l_idPhantom, l_day, l_count in l_cursor:
        l_dayFRCount = l_count
        if l_count >= G_MAX_FR_PER_DAY:
            l_cursor.close()
            return

    l_cursor.close()

    # prepare FR actions
    l_cursor = g_connectorRead.cursor()
    l_query = """
        select "L"."ID_USER"
            , "U"."ST_NAME"
            , "U"."TTCOUNT"
            , count(1) as "COUNT_LIKES"
        from
            "FBWatch"."TB_PRESENCE_LIKE" "L"
            join "FBWatch"."TB_USER_AGGREGATE" "U" on "U"."ID" = "L"."ID_USER"
            join "FBWatch"."TB_PHANTOM" "P" on "P"."ID_PHANTOM" = "L"."ID_PHANTOM"
            left outer join "FBWatch"."TB_OBJ" "O" on "O"."ID" = "U"."ID"
            left outer join "FBWatch"."TB_PRESENCE_FRIEND" "F" on "F"."ID_USER" = "U"."ID" and "F"."ID_PHANTOM" = "P"."ID_PHANTOM"
        where
            "O"."ID" is null -- Eliminates users which are actually pages
            and "F"."ID_USER" is null -- Eliminates users which have already received a request
            and "L"."ID_PHANTOM" = '{0}'
        group by
            "L"."ID_USER"
            , "U"."ST_NAME"
            , "U"."TTCOUNT"
        having
            count(1) >= 5
        order by count(1) desc, "U"."TTCOUNT" desc
        limit {1}
    """.format(p_phantomId, G_LIMIT_FRIEND)
    #print(l_query)
    l_cursor.execute(l_query)

    for l_idUser, l_userName, l_ttCount, l_countLikes in l_cursor:
        p_csvWriter.writerow(
            ['FRIEND', '', l_idUser, '{0} (TTCOUNT = {1} / Likes = {2})'.format(
                l_userName, l_ttCount, l_countLikes), '', '{0}'.format(l_dayFRCount)])

    l_cursor.close()

#def genRiversLink():
def prepareRiversActions(p_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId):
    print('--- Rivers Collective Image Actions ---')

    l_linkList = [
        'https://www.facebook.com/photo.php?fbid=793238987485271',
        'https://www.facebook.com/photo.php?fbid=793238920818611',
        'https://www.facebook.com/photo.php?fbid=793238497485320',
        'https://www.facebook.com/photo.php?fbid=793238374151999',
        'https://www.facebook.com/photo.php?fbid=793238244152012',
        'https://www.facebook.com/photo.php?fbid=793237847485385',
        'https://www.facebook.com/photo.php?fbid=793236704152166',
        'https://www.facebook.com/photo.php?fbid=793236634152173',
        'https://www.facebook.com/photo.php?fbid=793236294152207',
        'https://www.facebook.com/photo.php?fbid=793236250818878'
    ]
    for i in range(3):
        l_link = random.choice(l_linkList)
        l_linkList.remove(l_link)

        p_csvWriter.writerow(['RIVER', '', '', '', '', l_link])

g_commList = [
    'Indeed', 'That sounds so right', 'I agree', '100% agree',
    'Quite right', 'Absolutely right', 'Hell yes', 'Right on the mark', 'Yes indeed',
    'Yes', 'My God, Yes', 'True', 'So true', 'Yeah', 'Hell Yeah', 'Fuck Yeah', 'Thumbs up man',
    "Can't say anything against that", "Couldn't agree more",
    'There is no denying it', 'The Truth always comes out', "They can't hide",
    "Couldn't have said it better myself", 'You are right', 'You are so right',
    'Damn right', 'Spot on', 'You are damn right', 'Sure enough', 'Well said',
    "You've hit the nail right on the head", "That's the damn truth"]

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

        l_simpleComList = g_commList + [c + '!' for c in g_commList] + [c + '!!' for c in g_commList]

        for i in range(4):
            l_simpleComList = l_simpleComList + l_simpleComList

        g_choiceCommList = l_compoList + l_simpleComList


    l_commentNew = random.choice(g_choiceCommList)

    if random.randint(0, 19) == 10:
        l_index = random.randint(0, len(l_commentNew)-1)
        l_cnList = list(l_commentNew)
        l_cnList[l_index] = g_transChar[l_cnList[l_index]]
        l_commentNew = ''.join(l_cnList)

    if random.randint(0, 19) >= 10:
        l_commentNew = re.sub(r'\.$', '', l_commentNew)

    return l_commentNew

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

def prepareActions(p_phantomId, p_phantomPwd, p_vpn, p_fbId, p_noLikes, p_noComments, p_noRivers, p_noFirends):
    l_csvFile = 'bp_actions_' + re.sub('\W', '-', p_phantomId) + '.csv'

    print('Preparing actions for:', p_phantomId)
    with open(l_csvFile, 'w') as l_fOut:
        l_csvWriter = csv.writer(l_fOut,
            delimiter=';',
            quotechar='"',
            lineterminator='\n',
            quoting=csv.QUOTE_NONNUMERIC)

        l_csvWriter.writerow(['ACTION', 'FB_ID', 'DATA0', 'DATA1', 'DATA2', 'DATA3'])
        l_csvWriter.writerow(['LOG-IN', '', p_phantomId, p_phantomPwd, p_vpn, p_fbId])

        if not p_noLikes:
            prepareLikeActions(l_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId)
        if not p_noComments:
            prepareCommActions(l_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId)
        if not p_noRivers:
            prepareRiversActions(l_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId)
        if not p_noFirends:
            prepareFriendActions(l_csvWriter, p_phantomId, p_phantomPwd, p_vpn, p_fbId)

def executeActions():
    # record IP without VPN
    print('Getting base IP ...')
    l_baseIP = getOwnIp()
    print('Base IP:', l_baseIP)

    for l_file in glob.glob('bp_actions_*.csv'):
        print('Executing:', l_file)

        r, w = os.pipe()
        r, w = os.fdopen(r, 'r'), os.fdopen(w, 'w')

        l_locChildPid = os.fork()
        if l_locChildPid:  # Parent
            w.close()
            print('Child PID:', l_locChildPid)
            l_signal = r.readline().strip()
            print('Child completed:', l_signal)

            # check that the normal IP has come back
            l_currentIP = getOwnIp()
            if l_baseIP is not None and l_currentIP is not None and l_currentIP != l_baseIP:
                print('ERROR - VPN improperly closed')
                sys.exit()

        else:  # Child
            r.close()
            executeActionFile(l_file)
            w.write('OK')
            sys.exit()

def executeActionFile(p_file):
    global g_phantomId
    global g_phantomPwd
    global g_browserDriver

    # process object for the vpn when launched
    l_vpnProcess = None

    with open(p_file, 'r') as l_actionFile:
        # file name for the log
        l_logFilePath = re.sub('bp_actions_', 'bp_log_', p_file)
        l_logExists = os.path.isfile(l_logFilePath)

        l_friendRequesCount = 0
        with open(l_logFilePath, 'a') as l_logFile:
            l_csvLogWriter = csv.writer(l_logFile,
                delimiter=';',
                quotechar='"',
                lineterminator='\n',
                quoting=csv.QUOTE_NONNUMERIC)

            l_csvActionReader = csv.reader(l_actionFile,
                delimiter=';',
                quotechar='"',
                lineterminator='\n',
                quoting=csv.QUOTE_NONNUMERIC)

            # skip action file headers
            next(l_csvActionReader, None)
            if not l_logExists:
                # if log just created --> add header row
                l_csvLogWriter.writerow(['ACTION', 'PHANTOM_ID', 'OBJ_ID', 'USER_ID', 'DATA'])

            l_rowList = []
            l_phantomId = None
            l_phantomPwd = None
            l_vpn = None
            l_fbId = None
            # slurp in all rows in the action file ...
            for l_row in l_csvActionReader:
                # ... except the one containing the log-in data
                if l_row[0] == 'LOG-IN':
                    l_phantomId = l_row[2]
                    l_phantomPwd = l_row[3]
                    l_vpn = l_row[4]
                    l_fbId = l_row[5]
                    print('Logging in as:', l_phantomId, l_phantomPwd, l_vpn)

                    # store log-in parameters in globals so that likeOrComment() can access them
                    g_phantomId = l_phantomId
                    g_phantomPwd = l_phantomPwd
                else:
                    l_rowList += [l_row]

            l_actionFile.close()

            # turn on vpn
            if l_vpn is not None:
                print('Starting vpn')
                l_vpnProcess = switchonVpn(l_vpn, p_verbose=True)

            if l_vpnProcess is None:
                print('No VPN --> ABORTING ...')
            else:
                l_actionTotalCount = len(l_rowList)
                # execute actions at random
                for i in range(l_actionTotalCount):
                    l_noWait = False
                    l_row = random.choice(l_rowList)

                    l_action = l_row[0]
                    l_objId = l_row[1]
                    l_idUser = l_row[2]
                    l_userName = l_row[3]
                    l_commTxt = l_row[4]

                    # perform like action
                    if l_action == 'LIKE':
                        print('L <{4:<3}/{5:<3}> [{0:<20}] {1:<30} --> [{2:<40}] {3}'.format(
                            l_idUser, l_userName, l_objId, l_commTxt, i, l_actionTotalCount-1))

                        if likeOrComment(l_objId, p_message=''):
                            l_csvLogWriter.writerow(['L', l_phantomId, l_objId, l_idUser, ''])

                    # perform comment action
                    elif l_action == 'COMM':
                        l_newComm = l_row[5]
                        print('K <{4:<3}/{6:<3}> [{0:<20}] {1:<30} --> [{2:<40}] {3} --> {5}'.format(
                            l_idUser, l_userName, l_objId, l_commTxt, i, l_newComm, l_actionTotalCount-1))

                        if likeOrComment(l_objId, p_message=l_newComm):
                            l_csvLogWriter.writerow(['K', l_phantomId, l_objId, l_idUser, l_newComm])

                    # perform rivers image action
                    elif l_action == 'RIVER':
                        l_link = l_row[5]
                        print('R <{0:<3}/{1:<3}> --> {2}'.format(i, l_actionTotalCount-1, l_link))

                        if postRiverLink(l_link):
                            l_csvLogWriter.writerow(['R', l_phantomId, '', '', l_link])

                    # perform friend request action
                    elif l_action == 'FRIEND':
                        try:
                            l_dayFRCount = int(l_row[5])
                        except:
                            l_dayFRCount = 0

                        if l_friendRequesCount == 0 and l_dayFRCount > 0:
                            l_friendRequesCount = l_dayFRCount

                        if l_friendRequesCount < G_MAX_FR_PER_DAY:
                            print('F <{0:<3}/{1:<3}> [{2}] --> {3}'.format(
                                i, l_actionTotalCount-1, l_friendRequesCount, l_userName))

                            if friendRequest(l_idUser):
                                l_friendRequesCount += 1
                                l_csvLogWriter.writerow(['F', l_phantomId, '', l_idUser, l_userName])
                            else:
                                # failed friend request attempt (no FR button, most of the time)
                                l_csvLogWriter.writerow(['X', l_phantomId, '', l_idUser, l_userName])
                        else:
                            print('F <{0:<3}/{1:<3}> --> {2} SKIPPING'.format(
                                i, l_actionTotalCount-1, l_userName))
                            # if max number of FR reached, no need to wait
                            l_noWait = True

                    else:
                        print('Unknown action:', l_action)

                    l_logFile.flush()

                    # remove the row just executed from the list
                    l_rowList.remove(l_row)

                    # write back remaining rows to file, to be able to execute them after resuming post crash
                    if len(l_rowList):
                        with open(p_file, 'w') as l_fOut:
                            l_csvWriter = csv.writer(l_fOut,
                                                     delimiter=';',
                                                     quotechar='"',
                                                     lineterminator='\n',
                                                     quoting=csv.QUOTE_NONNUMERIC)

                            l_csvWriter.writerow(['ACTION', 'FB_ID', 'DATA0', 'DATA1', 'DATA2', 'DATA3'])
                            l_csvWriter.writerow(['LOG-IN', '', l_phantomId, l_phantomPwd, l_vpn, l_fbId])

                            for r in l_rowList:
                                l_csvWriter.writerow(r)

                        # wait
                        if not l_noWait:
                            randomWait(G_WAIT_FB_MIN, G_WAIT_FB_MAX)
                    else:
                        # delete action file if no more actions
                        os.remove(p_file)
                        # no need to wait ...

    # close Selenium web driver
    if g_browserDriver is not None:
        g_browserDriver.close()
        g_browserDriver = None

    # turn off vpn
    if l_vpnProcess is not None:
        print('Stopping VPN')
        # use signal SIGTERM (15) to allow children to close as well
        subprocess.Popen(['sudo', 'kill', '-15', str(l_vpnProcess.pid)])
        print('IP:', getOwnIp())

def logActions():
    print('Logging actions to main DB')
    for l_logFilePath in glob.glob('bp_log_*.csv'):
        with open(l_logFilePath, 'r') as l_logFile:
            l_csvLogReader = csv.reader(l_logFile,
                delimiter=';',
                quotechar='"',
                lineterminator='\n',
                quoting=csv.QUOTE_NONNUMERIC)

            # skip action file headers
            next(l_csvLogReader, None)

            for l_row in l_csvLogReader:
                l_action = l_row[0]
                l_phantomId = l_row[1]
                l_objId = l_row[2]
                l_idUser = l_row[3]
                l_data = l_row[4]

                if l_action == 'L':
                    logOneLike(l_idUser, l_objId, l_phantomId)
                elif l_action == 'K':
                    logOneComment(l_idUser, l_objId, l_data, l_phantomId)
                elif l_action == 'R':
                    logOneRiver(l_data, l_phantomId)
                elif l_action == 'F':
                    logOneFriendRequest(l_idUser, l_phantomId)
                elif l_action == 'X':
                    # failed friend request attempt (no FR button, most of the time)
                    logOneFriendRequest(l_idUser, l_phantomId, p_failed=True)

        os.remove(l_logFilePath)

    print('Logging actions to main DB Complete')

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Basic facebook presence                                    |')
    print('|                                                            |')
    print('| v. 3.3 - 04/06/2016                                        |')
    print('+------------------------------------------------------------+')

    random.seed()

    locale.setlocale(locale.LC_ALL, '')
    print('Locale: {0}'.format(locale.getlocale()))

    l_parser = argparse.ArgumentParser(description='Download FB data.')
    l_parser.add_argument('-l', help='List phantoms and login as one', action='store_true')
    l_parser.add_argument('-q', help='Quiet: less progress info', action='store_true')
    l_parser.add_argument('--NoLikes', help='Do not perform likes actions', action='store_true')
    l_parser.add_argument('--NoComments', help='Do not perform comments actions', action='store_true')
    l_parser.add_argument('--NoRivers', help='Do not perform rivers images actions', action='store_true')
    l_parser.add_argument('--NoFriends', help='Do not perform frend request actions', action='store_true')
    l_parser.add_argument('--Test', help='No VPN and only KA as user', action='store_true')
    l_parser.add_argument('--GenComment', help='Test gen comment', action='store_true')
    l_parser.add_argument('--SshTest', help='Test remote command execution', action='store_true')
    l_parser.add_argument('--LOCTest', help='Test likeOrComment', action='store_true')
    l_parser.add_argument('--TestMonitor', help='Test memory monitoring', action='store_true')
    l_parser.add_argument('--TestFriend', help='Test sending friend request', action='store_true')

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.l = False
            self.q = False
            self.NoLikes = False
            self.NoComments = False
            self.GenComment = False
            self.NoRivers = False
            self.NoFriends = False
            self.Test = False
            self.SshTest = False
            self.LOCTest = False
            self.TestMonitor = False
            self.TestFriend = False

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    if c.TestMonitor:
        launchMemoryMonitor()
        l_quit = input('Finished? ')
        sys.exit()

    if c.l:
        choosePhantom()
        sys.exit()

    if c.q:
        g_verbose = False

    if c.GenComment:
        for i in range(1000):
            print(i, genComment())
        sys.exit()

    if c.TestFriend:
        g_phantomId = 'kabir.abdulhami@gmail.com'
        g_phantomPwd = '12Alhamdulillah'
        friendRequest("1000012423386570")
        sys.exit()

    if c.LOCTest:
        g_phantomId = 'kabir.abdulhami@gmail.com'
        g_phantomPwd = '12Alhamdulillah'
        likeOrComment('10154315425328690_10154326253248690', 'Well ?')
        likeOrComment('10154315425328690_10154326253248690', 'Are you really sure ?')
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

    # start of normal execution

    # create new action files only if there are no logs pending, i.e. if in a "clean" state
    if not glob.glob('bp_*.csv'):
        g_connectorRead = psycopg2.connect(
            host='192.168.0.52',
            database="FBWatch",
            user="postgres",
            password="murugan!")

        if c.Test:
            prepareActions('kabir.abdulhami@gmail.com', '12Alhamdulillah', '', '',
                           c.NoLikes, c.NoComments, c.NoRivers, c.NoFriends)
        else:
            l_cursor = g_connectorRead.cursor()

            l_query = """
                select * from "FBWatch"."TB_PHANTOM"
            """

            # No exception catching here to allow full stack trace printout
            l_cursor.execute(l_query)

            for l_phantomId, l_phantomPwd, l_vpn, l_fbId in l_cursor:
                l_phantomId = l_phantomId.strip()
                l_phantomPwd = l_phantomPwd.strip()

                prepareActions(l_phantomId, l_phantomPwd, l_vpn, l_fbId,
                               c.NoLikes, c.NoComments, c.NoRivers, c.NoFriends)

            l_cursor.close()

        g_connectorRead.close()

    launchMemoryMonitor()

    # action execution, with no DB connections
    executeActions()

    # log actions to main DB
    g_connectorWrite = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    logActions()

    g_connectorWrite.close()



