#!/usr/bin/env python3
import praw
from bg3po_oauth import login
import re
from datetime import datetime

SUBREDDIT = "boardgames"
POST_BODY = "/home/bg3po/bg3po-scripts/etc/bazaar_post_body.red"


def get_month():
    month = datetime.now().strftime("%B")
    return(month)


def get_body():
    f = open(POST_BODY)
    body = f.read()
    f.close()
    return body


def post_bazaar(r, month):
    subject = month + " Board Game Bazaar"
    body = get_body()
    post = r.submit(SUBREDDIT, subject, text=body)
    post.distinguish(as_made_by='mod')
    # post.set_contest_mode(state=True)
    return (post.id)


def change_sidebar(r, post_id, month):
    sr = r.get_subreddit(SUBREDDIT)
    sb = sr.get_settings()["description"]
    new_bazaar = r'['+month+' Bazaar](/'+post_id+')'
    new_sb = re.sub(r'\[[a-zA-Z]+ Bazaar\]\(\/[a-z0-9]+\)', new_bazaar, sb, 1)
    sr.update_settings(description=new_sb)


def main():
    month = get_month()
    r = login()
    post_id = post_bazaar(r, month)
    change_sidebar(r, post_id, month)


if __name__ == '__main__':
    main()
