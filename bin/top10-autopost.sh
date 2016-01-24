#!/usr/bin/env bash

# cron scripts should not assume anything about PATH
# Note: this looks in ~glawler for top_rated. Update libBGG and fix this. 
PATH=/usr/local/bg3po/bin:/usr/local/bin:${PATH}
LOGDIR=/usr/local/bg3po/log
CRON_LOG=${LOGDIR}/top10cron.log
TOP_RATED_LOG=${LOGDIR}/top_rated.log
UPDATE_TOP10_LOG=${LOGDIR}/update_top10.log
# 1290 == Redittors guild id
GUILD_ID=1290 
JSONRATING=/usr/local/bg3po/etc/ratings.json
SUBREDDIT=boardgames
CACHE=/tmp/bgg_cache

echo Started at $(date) > $CRON_LOG 2>&1

# we want to start with a new cache each time. We want to use the cache
# though so we don't refetch every game for every collection.
if [ -e ${CACHE} ]; then 
    rm -rf ${CACHE} > /dev/null 2>&1
fi

# top_rated grabs the collections from BGG and generates a top rated file 
# n == 5000 so we get them all.
/usr/local/bg3po/bin/top_rated -g ${GUILD_ID} -j ${JSONRATING} -c ${CACHE} -l warning -n 5000 > ${TOP_RATED_LOG} 2>&1 
ec=$?
if [ ${ec} -ne 0 ]; then 
    echo Error at $(date) >> ${CRON_LOG}
    echo Error running top_rated script. Exited with ${ec}. Check ${TOP_RATED_LOG} for details. >> ${CRON_LOG}
    exit 1
fi

# - the top rated file is fed to update_top10 which computes +/- from 
# last month and writes the updates to reddit.
# - update_top10.py knows which USER and PASS it needs based on other
# files in its directories. 
/usr/local/bg3po/bin/update_top10.py -f ${JSONRATING} -s ${SUBREDDIT} -l debug > ${UPDATE_TOP10_LOG} 2>&1
ec=$?
if [ ${ec} -ne 0 ]; then 
    echo Error at $(date) >> ${CRON_LOG}
    echo Error running update top 10 script. Exited with ${ec}. >> ${CRON_LOG}
    exit 2
fi

echo Exiting with 0 at $(date) >> $CRON_LOG 2>&1

exit 0




