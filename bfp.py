import os
import sys
import argparse
import hashlib
import json
import time

import asks
import trio

import curlparser


REQ_TO_HASH = 'request_to_hash' 
HASH_TO_HTML = 'hash_to_html' 


def bf(curl, username=None, password=None):
    if username is None and password is None:
        raise ValueError("'username' and 'password' cannot be both None")

    if password is None:
        if not os.path.exists(username):
            raise ValueError("'username' must be a path to a list of usernames")

        trio.run(bf_username, curl, username)

async def bf_username(curl, username_file, password=None):
    http_args = parse_curl_file(curl)
    s = asks.Session(http_args.url, headers=dict(http_args.header), connections=10)


    db = {}
    db[REQ_TO_HASH] = {}
    db[HASH_TO_HTML] = {}

    async with trio.open_nursery() as nursery:
        with open(username_file) as file:
            for i, username in enumerate(file):
                nursery.start_soon(worker, s, i, db, username)

    persist_db(db)

def persist_db(db):
    output_dir = os.getcwd() + '/output'

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    timestr = time.strftime('%H_%M_%S-%Y_%m_%d')
    output_filename = output_dir + '/' + timestr + '.json'

    with open(output_filename, 'w') as out:
        json.dump(db, out, indent=4)

async def worker(session, key, db, username=None, password=None):
    data = f'username={username}&password={password}'
    r = await session.post(data=data)

    if r.status_code == 200:
        hasher = hashlib.md5()
        hasher.update(r.content)
        k = hasher.hexdigest()

        db[REQ_TO_HASH][data] = k
        db[HASH_TO_HTML][k] = r.text

def parse_curl_file(curl):
    if os.path.exists(curl):
        with open(curl) as f:
            curl_command = f.read()
            return curlparser.parse(curl_command)

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--curl', help='Path of the text containing the curl command as copied from the browser')
    parser.add_argument('-u', '--username', help='User or user list to be used')
    parser.add_argument('-p', '--password', help='Password or password list to be used')

    args, unknown = parser.parse_known_args(argv)

    bf(args.curl, args.username, args.password)

if __name__ == '__main__':
    main(sys.argv)

