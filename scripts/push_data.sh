#!/bin/bash

RESULTS_SERVER='soma2.rowland.org'
REMOTE_DATA_DIR='/media/raid/data/'

LOCAL_DATA_DIR='/data/raw/'

rsync -rtuv $LOCAL_DATA_DIR $RESULTS_SERVER:$REMOTE_DATA_DIR
