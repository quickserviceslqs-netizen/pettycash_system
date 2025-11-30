#!/usr/bin/env python
"""
Terminate active connections to the Django test database.
Run: python scripts/terminate_test_db_sessions.py

This attempts to connect to the Postgres server using the same credentials
from Django settings and issue pg_terminate_backend for any sessions using the
test database (typically `test_<NAME>`).

WARNING: This will forcibly disconnect other processes. Run only when you
intend to terminate dev/test connections.
"""
import os
import sys
import pathlib
import django

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pettycash_system.settings')
try:
    django.setup()
except Exception as e:
    print('Failed to setup Django:', e)
    sys.exit(2)

from django.conf import settings
from psycopg2 import connect, sql, OperationalError

DB = settings.DATABASES.get('default')
if not DB:
    print('No default database configured in settings.')
    sys.exit(2)

name = DB.get('NAME')
user = DB.get('USER') or os.environ.get('USER') or os.environ.get('USERNAME')
password = DB.get('PASSWORD') or os.environ.get('PGPASSWORD')
host = DB.get('HOST') or 'localhost'
port = DB.get('PORT') or 5432

# Test DB name Django creates is usually prefixed with 'test_'
if name.startswith('test_'):
    test_db = name
else:
    test_db = f'test_{name}'

print(f'Targeting test database: {test_db} on host={host} port={port} as user={user}')

try:
    # connect to maintenance DB (postgres) to be able to terminate others
    conn = connect(dbname='postgres', user=user, password=password, host=host, port=port)
    conn.autocommit = True
    cur = conn.cursor()

    # Find pids connected to the test DB excluding our own PIDs
    cur.execute("SELECT pid, usename, application_name, client_addr FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid();", (test_db,))
    rows = cur.fetchall()
    if not rows:
        print('No other sessions found connected to the test DB.')
    else:
        print(f'Found {len(rows)} session(s) to terminate:')
        for pid, usename, app, client_addr in rows:
            print(f' - pid={pid} user={usename} app={app} addr={client_addr}')

        confirm = input('Really terminate these sessions? Type YES to confirm: ')
        if confirm != 'YES':
            print('Aborting per user request.')
            cur.close()
            conn.close()
            sys.exit(0)

        terminated = 0
        for pid, _, _, _ in rows:
            try:
                cur.execute(sql.SQL('SELECT pg_terminate_backend(%s);'), (pid,))
                terminated += 1
            except Exception as e:
                print(f'Failed to terminate pid {pid}: {e}')

        print(f'Terminated {terminated} sessions.')

    cur.close()
    conn.close()
    sys.exit(0)

except OperationalError as e:
    print('Failed to connect to Postgres to terminate sessions:', e)
    sys.exit(2)
except Exception as e:
    print('Error while attempting to terminate sessions:', e)
    sys.exit(3)
