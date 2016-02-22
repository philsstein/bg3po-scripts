#!/usr/bin/env python

import praw
from argparse import ArgumentParser
from bg3po_oauth import login


if __name__ == "__main__":

    ap = ArgumentParser()
    ap.add_argument('-f', '--flair', help='Find users with the given flair')
    ap.add_argument('-s', '--subreddit', help='Search in given subreddit')
    args = ap.parse_args()

    r = login()
    sub = 'boardgames' if not args.subreddit else args.subreddit

    if args.flair:
        users = []
        for flair in r.get_subreddit(sub).get_flair_list(limit=None):
            if flair['flair_css_class'] == args.flair:
                users.append(flair['user'])

        users.sort()

        print('Users with {} flair:'.format(args.flair))
        for u in users:
            print('* /u/{}'.format(u))
