#!/usr/bin/env python3

# checks /u/bg3po's PMs and sends a notice to the sender to let them
# know that their message has not been read by their intended 
# recipient

import praw
import sys
import re
from bg3po_oauth import login

SUBREDDIT='boardgames'
AUTOREPLY_MSG = """\
You have PM'ed /u/bg3po.  This user is a bot account for doing administrative
tasks for the moderators of /r/boardgames. No human checks this account.

Please double check who you intended to send the message to. If your message
is of an administrative nature for /r/boardgames, please 
[message the moderators](http://www.reddit.com/message/compose?to=%2Fr%2Fboardgames)"""

def set_ks_link(r, msg):
    '''Extract day and link from message body and update sidebar with it.'''
    print('Setting KS roundup link in sidebar')
    sr = r.get_subreddit(SUBREDDIT)
    sb = sr.get_settings()['description']
    m = re.search('Date: ([0-9/]+)[ \n]', msg.body)
    if not m:
        print('Unable to find date in message body.')
        return

    day = m.group(1)
    m = re.search('Link: (.+)[\n]', msg.body)
    if not m:
        print('Unable to find link in message body.')
        return

    link = m.group(1)
    if len(link) != 6:
        print('Ignoring badly formatted KS Roundup URL. Must be only six chars.')
        return

    # [Kickstarter Roundup 10/25](/3q5p6x)
    new_ks_link = '[Kickstarter Roundup {}](/{})'.format(day, link)
    print('New link: {}'.format(new_ks_link))
    new_sb = re.sub(r'\[Kickstarter Roundup ([0-9/]+)\]\(\/[a-z0-9]+\)', new_ks_link, sb, 1)
    sr.update_settings(description=new_sb)

# all /r/bg mods can execute any command
mods = [
    'phil_s_stein'
]

# specific commands may be executable by non-mods. 
cmds = {
    'setksru': {
        'allowed': ['Zelbinian', 'whygook', 'anahuac-a-mole'] + mods,
        'cmd': set_ks_link
    }
}

def main():
    r = login()

    for msg in r.get_unread(unset_has_mail=True, update_user=True):
        if isinstance(msg, praw.objects.Message):
            # first check for bg3po commands.
            if msg.subject in cmds:
                if msg.author.name in cmds[msg.subject]['allowed']:
                    cmds[msg.subject]['cmd'](r, msg)

            else:   # All other messages the bg3po get the auto-response.
                msg.reply(AUTOREPLY_MSG)

            msg.mark_as_read()

if __name__ == '__main__':
    main()
