#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import sys
import re

#import mysql.connector
import psycopg2

# ---------------------------------------------------- Functions -------------------------------------------------------
def updateThemes():
    l_cursor = g_connectorRead.cursor()

    # read non page objects from TB_OBJ in 100 row batches
    l_query = """
        SELECT * from "FBWatch"."TB_THEME" order by "ID";
    """

    try:
        l_cursor.execute(l_query)

        for l_id, l_name, l_qUpdate, l_fCrackpot in l_cursor:
            l_qUpdate = l_qUpdate.strip()

            print('--------[ {0}/{1} ]-----------------------------'.format(l_id, l_name))

            l_match = re.search('SELECT\s+(\d+),', l_qUpdate)
            if l_match:
                l_qId = l_match.group(1)
                print('l_qId    :', l_qId)

                l_qUpdateN = re.sub(r'into\s+`(\w+)`\s+\(', r'into "FBWatch"."\1" (', l_qUpdate, flags=re.IGNORECASE)
                l_qUpdateN = re.sub(r'FROM\s+`(\w+)`', r'from "FBWatch"."\1"', l_qUpdateN, flags=re.IGNORECASE)
                l_qUpdateN = re.sub(r'`', r'"', l_qUpdateN)
                l_qUpdateN = re.sub(r"\\'", r"''", l_qUpdateN)

                if l_qUpdateN != l_qUpdate:
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

                print('l_qUpdateN:', l_qUpdateN)

                if int(l_id) != int(l_qId):
                    print('wrong ID in:', l_qUpdateN)
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
                    l_curWrite.execute(l_qUpdateN)
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

# ---------------------------------------------------- Main ------------------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| updates post ---> themes table                             |')
    print('|                                                            |')
    print('| v. 2.2 - 06/06/2016                                        |')
    print('| --> migrated to PostgreSQL                                 |')
    print('+------------------------------------------------------------+')

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

    updateThemes()

    print('*** Rebuilding TB_USER_AGGREGATE')

    print('Emptying TB_USER_AGGREGATE')
    l_query = 'delete from "FBWatch"."TB_USER_AGGREGATE";'
    performQuery(l_query)

    print('Copying V_USER_UNIQUE into TB_USER_AGGREGATE')
    l_query = """
        insert into "FBWatch"."TB_USER_AGGREGATE"
        select *, 0, 0, 0, 0, 0 from "FBWatch"."V_USER_UNIQUE";
    """
    performQuery(l_query)

    print('Calculating comment totals')
    l_query = """
        update "FBWatch"."TB_USER_AGGREGATE" as "U"
        set
            "AUTHCOUNT" = "O"."AUTHCOUNT",
            "PGCOUNT" = "O"."PGCOUNT"
         from (
                select
                    "ID_USER"
                    , count(1) as "AUTHCOUNT"
                    , count(DISTINCT "ID_PAGE") as "PGCOUNT"
                from "FBWatch"."TB_OBJ"
                group by "ID_USER"
            ) as "O"
        where "U"."ID" = "O"."ID_USER";
    """
    performQuery(l_query)

    print('Calculating like totals')
    l_query = """
        update "FBWatch"."TB_USER_AGGREGATE" as "U"
        set
            "LIKECOUNT" = "O"."LIKECOUNT",
            "PGLKCOUNT" = "O"."PGLKCOUNT"
        from(
                select
                    "R"."ID" as "ID_USER"
                    , count(distinct "J"."ID") as "LIKECOUNT"
                    , count(DISTINCT "J"."ID_PAGE") as "PGLKCOUNT"
                from
                    "FBWatch"."TB_OBJ" as "J" join "FBWatch"."TB_LIKE" as "L" on "J"."ID_INTERNAL" = "L"."ID_OBJ_INTERNAL"
                    join "FBWatch"."TB_USER" as "R" on "R"."ID_INTERNAL" = "L"."ID_USER_INTERNAL"
                group by "R"."ID"
        ) as "O"
        where "U"."ID" = "O"."ID_USER";
    """
    performQuery(l_query)

    print('Calculating TTCOUNT')
    l_query = """
        update "FBWatch"."TB_USER_AGGREGATE"
        set "TTCOUNT" = "LIKECOUNT" + "AUTHCOUNT";
    """
    performQuery(l_query)

    print('Removing users with less than 10 activity')
    l_query = """
        delete from "FBWatch"."TB_USER_AGGREGATE"
        where "TTCOUNT" < 10;
    """
    performQuery(l_query)