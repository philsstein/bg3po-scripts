import praw

subname = 'boardgames'
reddit = praw.Reddit(u'flair counter script - /u/phil_s_stein')
reddit.login()  # use ambient praw.ini or stdin/getpass
subreddit = reddit.get_subreddit(subname)

flairs = {}
flair_choices = subreddit.get_flair_choices()
for fc in flair_choices['choices']:
    if fc['flair_css_class']:
        flairs[fc['flair_css_class'][6:]] = 0

for f in subreddit.get_flair_list(limit=None):
    if f['flair_css_class']:
        if f['flair_css_class'] not in flairs:
            print('Found error in flairs: {}'.format(f))
            flairs[f['flair_css_class']] = 0

        flairs[f['flair_css_class']] += 1

count_sorted_flairs = sorted(flairs.items(), key=lambda x: x[1], reverse=True)
name_sorted_flairs = sorted(flairs.items(), key=lambda x: x[0])

for l in [count_sorted_flairs, name_sorted_flairs]:
    print('--------------------------')
    for name, count in l:
        print '* {}: {}'.format(name, count)

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

print('\n\nTotal users with flair: {}'.format(total))
