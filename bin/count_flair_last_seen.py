import praw
from datetime import datetime
from bg3po_oauth import login

subname = 'boardgames'
low_floir_count = 2     # threshold for low count when looking at user flair.

reddit = login()
print('logged in')
subreddit = reddit.get_subreddit(subname)

flairs = {}
most_recent = {}
flair_choices = subreddit.get_flair_choices()
for fc in flair_choices['choices']:
    if fc['flair_css_class']:
        flairs[fc['flair_css_class'][6:]] = 0
        most_recent[fc['flair_css_class'][6:]] = {'time': 0, 'user': None}

flairs['custom'] = 0
most_recent['custom'] = {'time': 0, 'user': None}

flair_list = list(subreddit.get_flair_list(limit=None))
print('Counting {} flairs'.format(len(flair_list)))
for f in flair_list:
    if f['flair_css_class']:
        if f['flair_css_class'] not in flairs:
            print('Found error in flairs: {}'.format(f))
            flairs[f['flair_css_class']] = 0
            most_recent[f['flair_css_class']] = {'time': 0, 'user': None}

        flairs[f['flair_css_class']] += 1

# now run over the flairs again and get most recent comment/submission for 
# low count flairs.
print('Finding last seen for low count flairs')
for f in flair_list:
    fclass = f['flair_css_class']
    if fclass in flairs and flairs[fclass] <= low_floir_count:
        # get most recent comment/submission for this user.
        user = reddit.get_redditor(f['user'])
        print('reading last seen for flair/count/user: {}/{}/{}'.format(fclass, flairs[fclass], f['user']))
        try:
            c = list(user.get_comments(limit=1))
            ctime = c[0].created_utc if len(c) else 0
        except praw.errors.NotFound:
            print('error. skipping {} comments'.format(f['user']))
            ctime = 0

        try:
            s = list(user.get_submitted(limit=1))
            stime = s[0].created_utc if len(s) else 0
        except praw.errors.NotFound:
            print('error. skipping {} comments'.format(f['user']))
            stime = 0

        last_seen = ctime if ctime > stime else stime
        if last_seen > most_recent[fclass]['time']:
            most_recent[fclass] = {'time': last_seen, 'user': f['user']}

count_sorted_flairs = sorted(flairs.items(), key=lambda x: x[1], reverse=True)
name_sorted_flairs = sorted(flairs.items(), key=lambda x: x[0])

for l in [count_sorted_flairs, name_sorted_flairs]:
    print('--------------------------')
    for name, count in l:
        print('* {}: {}'.format(name, count))

print('--------------------------')
# output markup for reddit
print('|Sorted by Count||_____|Sorted by Name||')
print('|------|-----|----|------|-----|')
print('|Name|Count||Name|Count|')
total = 0
for i in range(len(count_sorted_flairs)):
    total += count_sorted_flairs[i][1]
    print('{}|{}||{}|{}'.format(
        count_sorted_flairs[i][0], count_sorted_flairs[i][1],
        name_sorted_flairs[i][0], name_sorted_flairs[i][1]))

print('Last seen comment/sub with flair:')
print('|Name|Count|Last Seen|User|Timestamp')
print('|----|-----|---------|----|--------|')
for i in range(len(count_sorted_flairs)):
    if count_sorted_flairs[i][1] <= low_floir_count:
        d = datetime.fromtimestamp(most_recent[count_sorted_flairs[i][0]]['time']).ctime()
        print('{}|{}|{}|{}|{}'.format(
            count_sorted_flairs[i][0],
            count_sorted_flairs[i][1],
            d,
            most_recent[count_sorted_flairs[i][0]]['user'],
            most_recent[count_sorted_flairs[i][0]]['time']))

print('\n\nTotal users with flair: {}'.format(total))

exit(0)
