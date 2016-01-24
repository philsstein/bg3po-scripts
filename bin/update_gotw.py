import logging
import argparse
import re
from sys import exit
from html import unescape, escape  # python 3.4+
from urllib.error import HTTPError
from bg3po_oauth import login

import praw

from ArgParseLogging import addLoggingArgs, handleLoggingArgs
from GotW import getGotWPostText, updateGotWWiki, updateGotWSidebar, getNotFoundGames


log = logging.getLogger('gotw')

if __name__ == '__main__':
    '''A simple script that posts the game of the week for /r/boardgames'''
    ap = argparse.ArgumentParser()
    ap.add_argument(u'-w', u'--wiki', help=u'The wiki page from which to read/write the calendar info') 
    ap.add_argument(u'-s', u'--subreddit', help=u'The subreddit to update. Must have the gotw wiki '
                    u'page.')
    addLoggingArgs(ap)
    args = ap.parse_args()
    handleLoggingArgs(args)
    reddit_retry_timeout = 10 

    wiki_path = args.wiki if args.wiki else u'game_of_the_week'
    subreddit = args.subreddit if args.subreddit else u'boardgames'

    reddit = login()

    while True:
        try:
            gotw_wiki = reddit.get_wiki_page(subreddit, wiki_path)
            break
        except HTTPError:
            sleep(reddit_retry_timeout)

    log.debug(u'got wiki data: {}'.format(gotw_wiki.content_md))

    # finding the next GOTW is done in two parts. Find the wiki chunk, then find the list 
    # of games within that chunk
    search_for = u'\[//]:\s\(CALS\)\s+\s+\*\s+.*\[//]:\s\(CALE\)'
    match = re.search(search_for, gotw_wiki.content_md, flags=re.DOTALL)
    if not match:
        log.critical(u'Unable to find the upcoming GOTW in the wiki page "{}". Are there embedded'
                     u' delimiters in the page [//]: (CALS) and [//]: (CALE)?'.format(wiki_path))
        while True:
            try:
                reddit.send_message(u'#' + subreddit, subject=u'Unable to post GotW',
                                    message=u'There was a problem posting the GotW. Take a look at '
                                            u'the gotw wiki page. There is something amiss.')
                break
            except HTTPError:
                sleep(10)
        exit(1)

    cal_games = re.findall(u'\*\s+(.*)\s+', match.group(0))
    if not cal_games:
        log.critical(u'There are no games of the week queued up. Nothing to do.')
        exit(2)

    cal_games = [g.rstrip('\r\n') for g in cal_games]

    # first confirm the games are searchable. If not give up!
    not_found = getNotFoundGames(cal_games)
    if not_found:
        log.info(u'Sending mod mail. We could not find game(s) {}'.format(', '.join(not_found)))
        while True:
            try:
                reddit.send_message(u'#' + subreddit, subject=u'Error in GotW Calendar',
                                    message=u'Could not find the following game(s) on BGG: {}'
                                            u'. Please fix the GotW wiki calendar and re-run the GotW '
                                            u' script.'.format(', '.join(not_found)))
                break
            except HTTPError:
                sleep(reddit_retry_timeout)

        log.critical(u'Games on calendar not found. Bailing.')
        exit(3)


    next_gotw_name = cal_games[1] if len(cal_games) >= 2 else None
    log.info(u'found next game of the week: {}. Followed by {}'.format(
        cal_games[0], next_gotw_name))

    # grab the voting thread URL from the sidebar.
    vote_thread_url = None
    sb = reddit.get_settings(subreddit)['description']
    if sb:
        m = re.search('\[Vote here!\]\(/(?P<url>\w+)\)', sb)
        if m and 'url' in m.groupdict():
            vote_thread_url = m.group('url')

    log.debug('Vote here thread URL: {}'.format(vote_thread_url))

    # get the text of the GotW post.
    title, post_text = getGotWPostText(cal_games[0], next_gotw_name, vote_thread_url)

    if not post_text:
        log.critical(u'Error getting GotW post text')
        exit(4)

    # log.debug(u'Posting gotw text: {}'.format(post_text))
    while True:
        try:
            post = reddit.submit(subreddit, title=title, text=post_text)
            post.distinguish(as_made_by=u'mod')
            break
        except HTTPError:
            sleep(reddit_retry_timeout)

    log.info(u'Submitted gotw post for {}.'.format(cal_games[0]))

    # remind mods if fewer than 3 games left in calendar
    if len(cal_games) <= 3:   # this is *before* removing one so 4 is too many.
        log.info(u'Sending mod mail as there are fewer than 3 games in the GotW queue.')
        while True:
            try:
                reddit.send_message(u'#' + subreddit, subject=u'Top up the GotW Calendar', 
                                    message=u'Fewer than three games on the GotW. Please add more.')
                break
            except HTTPError:
                sleep(reddit_retry_timeout)

    new_wiki_page = updateGotWWiki(unescape(gotw_wiki.content_md), cal_games, post.id)
    if not new_wiki_page:
        log.critical(u'Unable to update GotW wiki page for some reason.')
        exit(5)

    while True:
        try:
            reddit.edit_wiki_page(subreddit=subreddit, page=wiki_path, content=new_wiki_page,
                                  reason=u'GotW post update for {}'.format(cal_games[0]))
            break
        except HTTPError:
            sleep(reddit_retry_timeout)

    log.info(u'GotW wiki information updated.')

    # finally update the sidebar/link menu
    sidebar = unescape(reddit.get_subreddit(subreddit).get_settings()["description"])
    new_sidebar = updateGotWSidebar(sidebar, cal_games[0], next_gotw_name, post.id)
    if new_sidebar == sidebar:
        log.critical(u'Error updating the sidebar for GotW.')
        exit(6)
    
    while True:
        try:
            reddit.get_subreddit(subreddit).update_settings(description=new_sidebar)
            break
        except HTTPError:
            sleep(reddit_retry_timeout)

    log.info(u'Sidebar updated with new GotW information.')

    exit(0)  # success!
