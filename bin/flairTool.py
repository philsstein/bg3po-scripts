#!/usr/bin/env python3

import os
import argparse
from sys import exit
from PIL import Image
import praw
import re
import logging
from bg3po_oauth import login

log = logging.getLogger(__name__)

def update_css(subreddit, css_lines):
    css = subreddit.get_stylesheet()['stylesheet']
    # /*FLAIR_OFFSET_START*/ ... /*FLAIR_OFFSET_END*/
    search_for = 'FLAIR_OFFSET_START\*/\n(.+)/\*FLAIR_OFFSET_END'
    replace_str = 'FLAIR_OFFSET_START*/\n%s/*FLAIR_OFFSET_END' % css_lines
    new_css, n = re.subn(search_for, replace_str, css, flags=re.DOTALL)
    if n == 1:
        log.info('Updating CSS with new flair offsets.')
        try:
            subreddit.set_stylesheet(new_css)
        except praw.errors.APIException as e:
            log.critical('Error updating CSS: %s' % e)
            f = os.path.join('.', 'error.css')
            with open(f, 'w') as fd:
                fd.write(new_css)
                log.info('Wrote new CSS to %s for inpection' % f)
            exit(1)
    else:
        log.critical('Error substituting new flair CSS.')
        exit(1)

def generate_flair(subreddit, img_dir):
    '''You know, the Nazis had pieces of flair that they made the Jews wear.'''
    # css_file = 'user-flair.css'
    flair_file = 'user-flair.png'
    img_size = 16
    img_space = 2

    # In which we open all images in imgdir and append them "down". 
    # And generate css offsets for each flair.
    subreddit.clear_flair_templates()
    css_lines = ''
    log.info('Processing:')
    for root, dirs, files in os.walk(img_dir):
        out_img = Image.new('RGBA', (img_size, len(files)*(img_size+img_space)))
        corner = 0
        flair_templates = []   # we temp store the template parameters so we can upload the image first.
        for f in sorted(files):
            name = os.path.splitext(f)[0]
            log.info('%s' % name)
            p = os.path.join(root, f)
            try:
                im = Image.open(p, 'r')
                im.load()
                if im.size != (img_size, img_size):
                    log.error('Skipping image %s. Images must be %dx%d' % (f, img_size, img_size))
                    continue
                out_img.paste(im, (0, corner))
            except OSError as e:
                log.error('Error processing %s: %s' % (f, e))
                continue

            css_lines += ('%-40s %-40s\n' % ('.flair-%s' % name,
                '{ background-position: 2px %dpx; }' % ((-corner)+img_space)))
            corner += img_size + img_space

            # 'mage-knight' --> 'Mage Knight' from filename to flair text
            temp_text = ' '.join([w.capitalize() for w in name.split('-')])
            flair_templates.append((temp_text, name))

        # with open(css_file, 'w') as cssfd:
        #    cssfd.write(css_lines)
        # log.info('Cached user-flair image to %s and flair related css to %s.' % (flair_file, css_file))
        out_img.save(flair_file)
        if subreddit.upload_image(image_path=flair_file, name='user-flair'):
            log.info('Uploaded new user-flair image file to %s' % subreddit)
            os.remove(flair_file)
        else:
            log.critical('ERROR: failed to upload user-flair image.')
            os.remove(flair_file)
            exit(1)

        # now update the CSS - will exit() on error
        update_css(subreddit, css_lines)

        log.info('Adding flair templates:')
        for text, css_class in flair_templates:
            log.info('adding %s (class: %s)' % (text, css_class))
            subreddit.add_flair_template(text=text, css_class=css_class, text_editable=True)

        subreddit.add_flair_template(text='(custom)', css_class='custom', text_editable=True)


if __name__ == '__main__':
    def_sub = 'timotab'
    user_agent = '@bg3po/flair update 0.2 Contact mods of /r/boardgames for info'
    def_image_dir = os.path.join('.', 'images')

    desc = ('(re)create the user flair of the given subreddit.')
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument('-i', '--images', dest='imagedir', help='The directory that contains the '
                    'flair images. Default is "%s"' % def_image_dir, default=def_image_dir)
    ap.add_argument('-s', '--subreddit', dest='subreddit', default=def_sub, help='Subreddit '
                    'to update. Default is "%s".' % def_sub)
    ap.add_argument("-l", "--loglevel", dest="loglevel",
                    help="The level at which to log. Must be one of "
                    "none, debug, info, warning, error, or critical. Default is none. ("
                    "This is mostly used for debugging.)",
                    default='info', choices=['none', 'all', 'debug', 'info', 'warning',
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
    
    reddit = login()

    # access to subreddit object
    subreddit = reddit.get_subreddit(args.subreddit)

    # generate_flair() will exit(1) on error.
    generate_flair(subreddit, args.imagedir) 

    exit(0)
