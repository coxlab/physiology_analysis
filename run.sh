#!/bin/bash

plotdir="/home/graham/Repositories/coxlab/physiology_analysis/visualization/"

cd $plotdir

for session in "$@"
do
    # run icapp.py on audio files
    if [ -e "/data/raw/$session/mixingmatrix" ] & [ -e "/data/raw/$session/unmixingmatrix" ]; then
        echo "Using existing ica matrices"
        # previous ica matrices exist, use them
        mkdir -p "/scratch/$session/Audio\ Files"
        cp /data/raw/$session/mixingmatrix /scratch/$session/mixingmatrix
        cp /data/raw/$session/unmixingmatrix /scratch/$session/unmixingmatrix
        python ~/Repositories/braingram/icapp/icapp.py -M /scratch/$session/mixingmatrix -U /scratch/$session/unmixingmatrix -o /scratch/$session/Audio\ Files/ /data/raw/$session/Audio\ Files/input_*
    else
        echo "Calculating ica matrices"
        python ~/Repositories/braingram/icapp/icapp.py -m random -s 441000 -o /scratch/$session/Audio\ Files/ /data/raw/$session/Audio\ Files/input_*
        echo "copying over ica matrices"
        cp /scratch/$session/Audio\ Files/mixingmatrix /data/raw/$session/
        cp /scratch/$session/Audio\ Files/unmixingmatrix /data/raw/$session/
    fi
    # copy over other files
    echo "Copying over auxillary files"
    cp /data/raw/$session/Audio\ Files/pixel* /scratch/$session/Audio\ Files/
    cp /data/raw/$session/$session.h5 /scratch/$session/
    echo "phy.py -f $session"
    phy.py -f $session
    #echo "copying over ica matrices"
    #cp /scratch/$session/Audio\ Files/mixingmatrix /data/raw/$session/
    #cp /scratch/$session/Audio\ Files/unmixingmatrix /data/raw/$session/
    echo "plot.sh $session"
    sh plot.sh $session
    # clean up
    rm -rf /scratch/$session/
done
