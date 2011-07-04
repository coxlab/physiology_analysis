#!/bin/bash

DATA_SERVER='coxlabphysiology1.rowland.org'

SERVER_DIR='/Volumes/Storage/data/physiology/'

LOCAL_DIR='/data/'

#rsync data from server to local dir
# rsync -rt /Users/labuser/Documents/setup_data/* vnsl.rowland.org:/Volumes/Drobo2/vnsl/Data/Behavior/setup_data/
rsync -rtu $DATA_SERVER:$SERVER_DIR $LOCAL_DIR