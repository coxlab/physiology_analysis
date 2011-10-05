#!/bin/bash

plotdir="/home/graham/Repositories/coxlab/physiology_analysis/visualization/"

cd $plotdir

for session in "$@"
do
    echo "phy.py -f $session"
    phy.py -f $session
    echo "plot.sh $session"
    sh plot.sh $session
done
