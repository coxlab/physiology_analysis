#!/bin/bash

SESSION=$1
echo "Plotting Session: $SESSION"

python plot_bluesquare.py $SESSION
python plot_atlas.py $SESSION
python plot_isi.py $SESSION
python plot_spike_trains.py $SESSION
parallel python plot_{3}.py $SESSION -g {1} -c {2} ::: pos_x pos_y size_x name ::: `seq 32` ::: psths rasters
