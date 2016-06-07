import praw
import re
from sys import exit, argv
from datetime import date
import logging
import argparse
import html
from bg3po_oauth import login

log = logging.getLogger('regotw')
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument(u'-w', u'--wiki', help=u'The wiki page from which to read/write the calendar info') 
    ap.add_argument(u'-s', u'--subreddit', help=u'The subreddit to update. Must have the gotw wiki '
                    u'page.')
    args = ap.parse_args()
    wiki_page = u'game_of_the_week' if not args.wiki else args.wiki
    subreddit = u'boardgames' if not args.subreddit else args.subreddit

    reddit = login()
    
    gotw_page = reddit.get_wiki_page(subreddit=subreddit, page=wiki_page)
    gotw_text = html.unescape(gotw_page.content_md)
    log.debug('Found wiki text:\n{}'.format(gotw_text))

    matches = re.findall(u'(\d{4}-\d{2}-\d{2}) \| \[([^\]]+)\]\(/(\w+)\)', gotw_text)
    if not matches:
        log.critical(u'Unable to find GOTW links in wiki page {}'.format(wiki_page))
        exit(1)

    log.debug('Found {} games'.format(len(matches)))

    # games are [ ['YYYY-MM-DD', 'game name', 'gotw url'], ... ]
    # make first data point into python date class instance.
    games = [list(x) for x in matches]
    log.debug('first five games found: {}'.format(games[0:4]))
    for game in games:
        y, m, d = game[0].split('-')
        try:
            game[0] = date(int(y), int(m), int(d))
            if game[0].month == 2 and game[0].day == 29:   # feb 29th == march 1
                game[0] = date(game[0].year, 3, 1)
        except ValueError:
            log.critical(u'Unable to parse date input from wiki: {}'.format(game[0]))
            exit(1)
    
    # sort by date. (It's not clear this gets us much.)
    games = sorted(games)
    log.debug(u'sorted games: {}'.format(games))

    today = date.today()
    try:
        two_years_ago = date(today.year-2, today.month, today.day)
    except ValueError:   # triggered for feb 29th
        two_years_ago = date(today.year-2, today.month+1, 1)

    log.debug(u'2 years ago: {}'.format(two_years_ago))

    for game in games:
        if game[0] < two_years_ago:
            log.debug(u'found GOTW older than two years: {}'.format(game[1]))
        elif game[0] == two_years_ago:
            log.debug(u'found two year old GOTW. Reposting {} GOTW post'.format(game[1]))
            break
        else:
            log.debug(u'no GOTW from two years ago. Next GOTW repost is {} on {}'.format(
                game[1], game[0]))
            exit(0)

    gotw_post = reddit.get_submission(submission_id=game[2], comment_limit=0)
    search_str = u'\[//]: # \(GOTWS\)\s+(.+)\[//]: # \(GOTWE\)\s+'
    m = re.search(search_str, gotw_post.selftext, flags=re.DOTALL)
    if not m:
        log.critical(u'Unable to find post body or body separator flags ([//]: # (GOTWS)...')
        exit(1)

    # figure suffix for the day for header inclusion.
    if 4 <= game[0].day <= 20 or 24 <= game[0].day <= 30:
        suffix = u"th"
    else:
        suffix = [u"st", u"nd", u"rd"][game[0].day % 10 - 1]

    repost_header = u'''
Note: {} was Game of the Week on /r/boardgames [two years ago today](/{}). This GoTW repost gives people of the sub a chance to discuss the game again after a bit of time has passed. Do you still play it? If so, how often does it make it to the table? Has the game held up after repeated plays? Has it moved up or down in your personal ranking? Has it been replaced by a newer, similar game? Has it replaced a game?

Below is [the original Game of the Week post](/{}) from {}:

------------------

'''.format(game[1], game[2], game[2], game[0].strftime(u'%B %d{}, %Y'.format(suffix)))

    repost_text = repost_header + m.group(1)
    log.debug(u'Reposting this GOTW text:\n{}'.format(repost_text))

    title = u'Game of the Week, Redux: {}'.format(game[1])
    repost = reddit.submit(subreddit, title, text=repost_text)
    repost.distinguish(as_made_by=u'mod')
