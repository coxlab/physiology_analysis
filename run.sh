#!/bin/bash

plotdir="/home/graham/Repositories/coxlab/physiology_analysis/visualization/"

pushd $plotdir

for session in "$@"
do
    echo "physio.py -f $1"
    physio.py -f $1
    echo "plot.sh $1"
    sh plot.sh $1
done

popd
