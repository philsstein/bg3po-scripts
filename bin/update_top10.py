#!/usr/bin/env python3

import praw
import re
from sys import exit
import argparse
import logging
import json
from datetime import datetime
from collections import defaultdict
from datetime import date, timedelta
from bg3po_auth import login

log = logging.getLogger(__name__)

def get_rank(name, ratings):
    '''find the index into the ordered by rank list of games and return it.
    None if not found.'''
    ranks = [i for i, r in enumerate(ratings['game_ratings'], 1) if r[0] == name]
    if not ranks:
        return None
    
    return ranks[0]

def dataToWiki(jsonstr, deltas, subreddit):
    '''Take a json file, parse it, and return a list of strings for 
    writing to a wiki page. Also return trruncated top 10 list as well.'''
    # data = {
    #     'game_ratings': top,    # [ [name, num raters, avg rating], [...], ... ]
    #     'rating_threshold': min_rating,
    #     'num_raters': int(len(collections)),
    #     'total_ratings': sum([len(x) for x in item_ratings.values()]),
    #     'game_ids': game_ids    # {name: bggid, name: bggid ...}
    # }
    data = json.loads(jsonstr)

    # sample line:
    # |180|[Clue](http://boardgamegeek.com/boardgame/1294)|5.42|**▲1**|205
    ret = ['|Rank|Game|Rating|+/-|Raters']
    ret.append('|--:|:-----------|---------------:|--:|-----:|')
    for rank, g in enumerate(data['game_ratings'], 1):
        ret.append('|{}|[{}](http://boardgamegeek.com/boardgame/{})|{:.2f}|{}|{}'.format(
            rank, g[0], data['game_ids'][g[0]]['bggid'], g[2], deltas[g[0]], g[1]))

    ret.append('\n')
    ret.append('\nA few stats on ratings for this month:')
    ret.append('\n * Total Raters (guild members with collections): {}'.format(data['num_raters']))
    ret.append('\n * Rating Threshold (%5 of raters): {}'.format(data['rating_threshold']))
    ret.append('\n * Total Ratings: {}'.format(data['total_ratings']))
    ret.append('\n[Previous Month\'s '
               'Rankings](http://reddit.com/r/{}/w/top_10/full_list_prev).'.format(subreddit))
    ret.append('\n[Archived Rankings](http://reddit.com/r/{}/w/top_10/archive).'.format(subreddit))
    ret.append('\nPosted at {}'.format(datetime.ctime(datetime.now())))

    top10 = ret[:12]
    top10.append('| | |\n| | [more...](/r/{}/w/top_10/full_list) |\n'.format(subreddit))
    top10.append('Posted at: {}'.format(datetime.ctime(datetime.now())))

    return top10, ret

def doTop10Post(subreddit, jsonstr, stats):
    header = '''
The /r/boardgames games ratings are updated each month on the 15th-ish. This month's full ratings have been posted [on the wiki](http://www.reddit.com/r/boardgames/wiki/top_10/full_list) and the new Top 10 list is on the sidebar. The archive of all game ratings can also be found [on the wiki as well](http://www.reddit.com/r/boardgames/wiki/top_10/archive).

The list is computed by averaging all rankings for all members of the [Redditors Guild on BoardgameGeek](http://www.boardgamegeek.com/guild/1290). In order for a game to be on the list, 5% of members must have rated it. If you'd like to participate in generating the list, [join the Guild and start rating](http://imgur.com/a/Xj7Io)!

'''
    footer = '''
Note that games entering and leaving the list affect the movement of all games beneath it. Games may drop off the list if new Guild members have not rated a game as the threshold required for inclusion has increased.

-------

What the [rankings mean according to BGG](http://boardgamegeek.com/wiki/page/ratings):

* 10 - Outstanding. Always want to play, expect this will never change.
* 9 - Excellent. Always want to play.
* 8 - Very good. Like to play, will probably suggest it, will never turn it down.
* 7 - Good. Usually willing to play.
* 6 - Fair. Some fun or challenge at least, will play occasionally if in the right mood.
* 5 - Average. No significant appeal, take it or leave it.
* 4 - Below average. Slightly boring, could be talked into it on occasion.
* 3 - Poor. Likely won't play this again although could be convinced.
* 2 - Very poor. Annoying, I plan to never play this again.
* 1 - Defies description of a game. You won't catch me dead playing this. Clearly broken.
'''
    data = json.loads(jsonstr)
    post = []
    post.append('Here are a few stats about this month\'s list.')
    post.append('\n * Total Raters (guild members with collections): {}'.format(data['num_raters']))
    post.append('\n * Rating Threshold (5% of raters): {}'.format(data['rating_threshold']))
    post.append('\n * Total Ratings: {}'.format(data['total_ratings']))

    if stats['new_games']:
        post.append('\n**New Games on the List:**')
        post.append('\n|**Name**|**Rank**|')
        post.append('|----|----|')
        for game in sorted(stats['new_games'], key=lambda x: x[1]):
            post.append('|{}|{}|'.format(game[0], game[1]))

    if stats['gone_games']:
        post.append('\n**Games that Left the List:**')
        post.append('\n|**Name**|**Rank**|')
        post.append('|----|----|')
        for game in sorted(stats['gone_games'], key=lambda x: x[1]):
            post.append('|{}|{}|'.format(game[0], game[1]))

    movers = sorted([d for d in stats['deltas'].values()], key=lambda x: x['Movement'], reverse=True)
    gainers = movers[:10]
    decliners = movers[::-1][:10]   # extended slice :: gives reversed list

    for title, movelist in [('Gainers', gainers), ('Decliners', decliners)]:
        if movelist[0]['Movement'] != 0:
            post.append('\n**Top {}:**'.format(title))
            post.append('\n|Name|Movement|New Rank|Old Rank|New Rating|Old Rating|')
            post.append('|'.join(['----' for _ in range(len(movelist[0].keys()))]))
            for game in movelist:
                if game['Movement'] == 0:
                    break
                post.append('{Name}|{Movement}|{New Rank}|{Old Rank}|{New Rating:.2f}|{Old Rating:.2f}'.format(**game))

    post = header + '\n'.join(post) + footer
    prev_month = (date.today() - timedelta(365/12)).strftime('%B')
    now_month = date.today().strftime('%B')
    title = '/r/{} rankings for {}/{} posted'.format(subreddit.display_name, prev_month, now_month)
    ratings_post = subreddit.submit(title=title, text=post)
    ratings_post.distinguish(as_made_by=u'mod')
                                                                                        
def get_deltas_and_stats(prev_json, cur_json):
    '''return a map of game name to delta string for use in wiki page.
    also return various stats.'''
    prev = json.loads(prev_json)
    cur = json.loads(cur_json)

    stats = {
        'new_games': [],
        'gone_games': [],
        'deltas': defaultdict(dict),
    }

    # compute deltas
    delta_strs = {}
    for cur_rank, game_rating in enumerate(cur['game_ratings'], 1):
        game_name = game_rating[0]
        prev_rank = get_rank(game_name, prev)
        stats['deltas'][game_name]['Name'] = game_name
        stats['deltas'][game_name]['Old Rank'] = prev_rank if prev_rank else None
        stats['deltas'][game_name]['New Rank'] = cur_rank
        stats['deltas'][game_name]['New Rating'] = float(game_rating[2])
        stats['deltas'][game_name]['Old Rating'] = None  # filled below
        stats['deltas'][game_name]['Movement'] = 0
        if not prev_rank:
            delta_strs[game_name] = '~~\N{BLACK STAR}~~'
        else:
            change = prev_rank - cur_rank
            stats['deltas'][game_name]['Movement'] = change
            if change == 0:  # no change
                delta_strs[game_name] = '---'
            elif change > 0:
                delta_strs[game_name] = '**\N{BLACK UP-POINTING TRIANGLE}%d**' % abs(change)
            else:
                delta_strs[game_name] = '*\N{BLACK DOWN-POINTING TRIANGLE}%d*' % abs(change)
    
    for rank, game_rating in enumerate(prev['game_ratings'], 1):
        game_name = game_rating[0]
        if not game_name in stats['deltas']:
            # this game has dropped off the list
            stats['deltas'][game_name]['Name'] = game_name
            stats['deltas'][game_name]['Old Rank'] = rank
            stats['deltas'][game_name]['New Rank'] = None
            stats['deltas'][game_name]['New Rating'] = None
            stats['deltas'][game_name]['Movement'] = 0

        stats['deltas'][game_name]['Old Rating'] = float(game_rating[2])
    
    # figure some basic stats. new games, gone games, etc.
    prev_set = set([g[0] for g in prev['game_ratings']])
    cur_set = set([g[0] for g in cur['game_ratings']])
    for game in list(cur_set - prev_set):
        stats['new_games'].append([game, get_rank(game, cur)])

    for game in list(prev_set - cur_set):
        stats['gone_games'].append([game, get_rank(game, prev)])

    stats['new_games'] = sorted(stats['new_games'], key=lambda g: g[1], reverse=True)
    stats['gone_games'] = sorted(stats['gone_games'], key=lambda g: g[1], reverse=True)
   
    return delta_strs, stats

if __name__ == '__main__':
    def_sub = 'boardgames'
    def_datapath = '/usr/local/bg3po/etc/top-rated-bgg.json'
    user_agent = '@bg3po/topten 0.3 Contact mods of /r/boardgames for info'

    desc = ('Update the Top 10 games list in BGG sidebar and top XXX list in r/bg wiki.')
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument('-m', '--mod', dest='mod', help='Name of BGG mod with auth to update.')
    ap.add_argument('-p', '--password', dest='password', help='Password of mod account given.')
    ap.add_argument('-f', '--top10file', dest='datapath', help='The location of the json-formatted '
                    'Top XXX file. Default is %s' % def_datapath, default=def_datapath)
    ap.add_argument('-s', '--subreddit', dest='subreddit', default=def_sub, help='Subreddit '
                    'to update. Default is %s' % def_sub)
    ap.add_argument("-l", "--loglevel", dest="loglevel",
                    help="The level at which to log. Must be one of "
                    "none, debug, info, warning, error, or critical. Default is none. ("
                    "This is mostly used for debugging.)",
                    default='none', choices=['none', 'all', 'debug', 'info', 'warning',
                                             'error', 'critical'])
    args = ap.parse_args()

    logLevels = {
        'none': 100,
        'all': 0,
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    log_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    log_datefmt = '%m-%d %H:%M:%S'
    logging.basicConfig(format=log_format, datefmt=log_datefmt,
                        level=logLevels[args.loglevel])
 
    with open(args.datapath, 'r') as fd:
        cur_json = fd.read()
    
    reddit = login()

    sr = reddit.get_subreddit(args.subreddit)

    prev_json = sr.get_wiki_page('top_10/cur_json').content_md
    deltas, stats = get_deltas_and_stats(prev_json, cur_json)
    top10, fullwiki = dataToWiki(cur_json, deltas, args.subreddit)

    # grab sidebar
    sb = sr.get_settings()['description']

    # now substitute new top 10 in place in the sidebar
    # we use the put-in-place delimiters to find the top 10.
    search_for = '\[//]: # \(TTS\)\n(.+)\s*\[//]: # \(TTE\)\n'
  
    # do the deed, update the sidebar
    top10 = '[//]: # (TTS)\n' + '\n'.join(top10) + '\n[//]: # (TTE)\n'
    log.info('new top 10:\n{}'.format(top10))
    new_sb = re.sub(search_for, top10, sb, flags=re.DOTALL)
    if new_sb == sb:
        log.critical('Failed to do top 10 subsitution.')
        exit(2)

    # update the sidebar on reddit
    sr.update_settings(description=new_sb)

    # now update the wiki. New -> new, prev -> prev and archive.
    prev_list = sr.get_wiki_page('top_10/full_list')
    sr.edit_wiki_page('top_10/full_list', '\n'.join(fullwiki))
    sr.edit_wiki_page('top_10/full_list_prev', prev_list.content_md)
    sr.edit_wiki_page('top_10/cur_json', cur_json)

    d = datetime.now()
    arch_dir = 'top_10/archive'
    arch_name = '%4d%02d%02d-%02d%02d' % (d.year, d.month, d.day, d.hour, d.minute)
    arch_path = '/%s/%s' % (arch_dir, arch_name)
    sr.edit_wiki_page(arch_path, prev_list.content_md)

    # update archive index.
    arch_rec = sr.get_wiki_page(arch_dir)
    arch_rec_list = arch_rec.content_md
    arch_rec_list += '\n * [%s](http://reddit.com/r/%s/wiki%s)' % (
        arch_name, args.subreddit, arch_path)
    sr.edit_wiki_page(arch_dir, arch_rec_list, reason='Added data for %s' % arch_name)

    doTop10Post(sr, cur_json, stats)

    exit(0)
