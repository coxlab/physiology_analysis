#!/bin/bash

plotdir="/home/graham/Repositories/coxlab/physiology_analysis/visualization/"

cd $plotdir

for session in "$@"
do
    echo "phy.py -f $1"
    phy.py -f $1
    echo "plot.sh $1"
    sh plot.sh $1
done
