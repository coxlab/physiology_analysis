#!/bin/bash

plotdir="/home/graham/Repositories/coxlab/physiology_analysis/visualization/"

cd $plotdir

for session in "$@"
do
    # run icapp.py on audio files
    python ~/Repositories/braingram/icapp/icapp.py -m random -s 441000 -o /scratch/$session/Audio\ Files/ /data/raw/$session/Audio\ Files/input_*
    # copy over other files
    cp /data/raw/$session/Audio\ Files/pixel* /scratch/$session/Audio\ Files/
    cp /data/raw/$session/$session.h5 /scratch/$session/
    echo "phy.py -f $session"
    phy.py -f $session
    echo "plot.sh $session"
    sh plot.sh $session
    # clean up
    # TODO
done
