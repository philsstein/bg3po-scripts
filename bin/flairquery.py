#!/usr/bin/env python

import praw
from argparse import ArgumentParser


if __name__ == "__main__":
    r = praw.Reddit('flair query tool by /u/phil_s_stein')
    r.login(disable_warning=True)

    ap = ArgumentParser()
    ap.add_argument('-f', '--flair', help='Find users with the given flair')
    ap.add_argument('-s', '--subreddit', help='Search in given subreddit')
    args = ap.parse_args()

    sub = 'boardgames' if not args.subreddit else args.subreddit

    if args.flair:
        users = []
        for flair in r.get_subreddit(sub).get_flair_list(limit=None):
            if flair['flair_css_class'] == args.flair:
                users.append(flair['user'])

        users.sort()

        print('Users with {} flair:')
        for u in users:
            print('* /u/{}'.format(u))
