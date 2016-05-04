#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import sys
import re

#import mysql.connector
import psycopg2

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| updates post ---> themes table                             |')
    print('|                                                            |')
    print('| v. 2.0 - 04/05/2016                                        |')
    print('| --> migrated to PostgreSQL                                 |')
    print('+------------------------------------------------------------+')

    l_verbose = False

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

    # read non page objects from TB_OBJ in 100 row batches
    l_query = """
        SELECT * from "FBWatch"."TB_THEME";
    """

    try:
        l_cursor.execute(l_query)

        for l_id, l_name, l_qUpdate, l_fCrackpot in l_cursor:
            l_qUpdate = l_qUpdate.strip()

            print('--------[ {0}/{1} ]-----------------------------'.format(l_id,l_name))

            l_match = re.search('SELECT\s+(\d+),\s+`ID`', l_qUpdate)
            if l_match:
                l_qId = l_match.group(1)
                print('l_qId    :', l_qId)

                l_qUpdate = re.sub(r'into\s+`(\w+)`\s+\(', r'into "FBWatch"."\1" (', l_qUpdate, flags=re.IGNORECASE)
                l_qUpdate = re.sub(r'FROM\s+`(\w+)`', r'from "FBWatch"."\1"', l_qUpdate, flags=re.IGNORECASE)
                l_qUpdate = re.sub(r'`', r'"', l_qUpdate)
                l_qUpdate = re.sub(r"\\'", r"''", l_qUpdate)

                l_query = """
                    update "FBWatch"."TB_THEME"
                    set "TX_REQUEST" = '{0}'
                    where "ID" = {1};
                """.format(
                    re.sub("'", "''", l_qUpdate), l_qId
                )
                # execute update query
                l_curWrite = g_connectorWrite.cursor()
                try:
                    l_curWrite.execute(l_query)
                    g_connectorWrite.commit()
                except Exception as e:
                    print('TB_THEME Unknown Exception: {0}'.format(repr(e)))
                    print(l_query)
                    sys.exit()

                l_curWrite.close()
                print('l_qUpdate:', l_qUpdate)

                if int(l_id) != int(l_qId):
                    print('wrong ID in:', l_qUpdate)
                    sys.exit()

                l_qCleanup = """
                    delete from "FBWatch"."TB_WORD_THEME" where "ID_THEME" = {0};
                """.format(l_id)

                # execute cleanup query
                l_curWrite = g_connectorWrite.cursor()
                try:
                    l_curWrite.execute(l_qCleanup)
                    g_connectorWrite.commit()
                except Exception as e:
                    print('TB_WORD_THEME Unknown Exception: {0}'.format(repr(e)))
                    print(l_qCleanup)
                    sys.exit()

                l_curWrite.close()

                # execute update query
                l_curWrite = g_connectorWrite.cursor()
                try:
                    l_curWrite.execute(l_qUpdate)
                    g_connectorWrite.commit()
                except Exception as e:
                    print('TB_WORD_THEME Unknown Exception: {0}'.format(repr(e)))
                    print(l_qUpdate)
                    sys.exit()

                l_curWrite.close()
            else:
                print('ID not found in:', l_qUpdate)
                sys.exit()
    except Exception as e:
        print('Unknown Exception: {0}'.format(repr(e)))
        print(l_query)
        sys.exit()

    l_cursor.close()