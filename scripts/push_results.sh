#!/bin/bash

RESULTS_SERVER='soma2.rowland.org'
REMOTE_RESULTS_DIR='/media/raid/results'

LOCAL_RESULTS_DIR='/data/results'

#rsync data from server to local dir
rsync -rtuv $LOCAL_RESULTS_DIR $RESULTS_SERVER:$REMOTE_RESULTS_DIR
