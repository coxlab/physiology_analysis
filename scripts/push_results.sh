#!/bin/bash

RESULTS_SERVER='soma2.rowland.org'
REMOTE_RESULTS_DIR='/media/raid/results'
REMOTE_DATA_DIR='/media/raid/data'

LOCAL_RESULTS_DIR='/data/analyzed'
LOCAL_DATA_DIR='/data/raw'

SERVER_DIR='/Volumes/Storage/data/physiology/'

LOCAL_DIR='/data/'

#rsync data from server to local dir
# rsync -rt /Users/labuser/Documents/setup_data/* vnsl.rowland.org:/Volumes/Drobo2/vnsl/Data/Behavior/setup_data/
rsync -rtuv $DATA_SERVER:$SERVER_DIR $LOCAL_DIR
