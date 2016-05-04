#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'fi11222'

import psycopg2

# ---------------------------------------------------- Main section ----------------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| FB watching scripts                                        |')
    print('|                                                            |')
    print('| Postgres connector test                                    |')
    print('|                                                            |')
    print('| v. 1.0 - 04/05/2016                                        |')
    print('+------------------------------------------------------------+')

    l_connector = psycopg2.connect(
        host='192.168.0.52',
        database="FBWatch",
        user="postgres",
        password="murugan!")

    l_cursor = l_connector.cursor()

    l_cursor.execute("""
        SELECT "ID", "ST_NAME"
        FROM
          "FBWatch"."TB_THEME";
      """)

    for l_record in l_cursor:
        print(l_record)

    l_cursor.close()

    l_connector.close()