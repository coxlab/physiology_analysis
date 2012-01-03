#!/bin/bash
# Script to analyze one or many sessions
#
# Usage:
#   run.sh ["all/new"]/[<sessions...>]
#
# if argument 1 is "all" then analyze all available sessions
# if argument 1 is "new" only anlyze sessions that don't have results
# or supply a list of session names (ex. L2_111210 L2_111211 etc...)
#
# location of sessions & results are read using phycfg.py (part of physio)
# analysis is performed with phy.py (part of physio)
# pre-analysis ICA noise reduction is done with icapp.py (part of icapp)


# icapp.py location
icapp="/home/graham/Repositories/braingram/icapp/icapp.py"
# arguments to icapp.py: python icapp.py -m $icamode -s $icaarg ...
icamode="random"
icaarg="441000"

# change cwd to visualization directory so calling plot scripts is easier
plotdir="/home/graham/Repositories/coxlab/physiology_analysis/visualization/"
cd $plotdir

# read config variables with phycfg.py
rawdir=`phycfg.py filesystem rawrepo`
echo "Raw directory: $rawdir"
datadir=`phycfg.py filesystem datarepo`
echo "Data directory: $datadir"
resultsdir=`phycfg.py filesystem resultsrepo`
echo "Results directory: $resultsdir"

# check $1: 'new', 'all', <sessions...>
if [ -z "$1" ]
then
    echo "Command line argument not supplied. Example: run.sh 'new/all/<sessions...>'"
    exit 1
elif [ "$1" = "new" ]
then
    sessions=`diff $resultsdir $rawdir | grep Only | awk '{print $4}' | grep -e "_[1-9]"`
    echo "New sessions: $sessions"
elif [ "$1" = "all" ]
then
    sessions=`python -c 'import physio; print " ".join(physio.session.get_sessions())'`
    echo "All sessions: $sessions"
elif [ "$1" = "invalid" ]
then
    sessions=`python -c 'import physio; print " ".join(physio.session.get_invalid_sessions())'`
    echo "Invalid sessions: $sessions"
else
    sessions=$@
fi

# analyze all sessions
for session in "$sessions"
do
    echo "Analyzing $session"
    # ica related files
    imm="$rawdir/$session/mixingmatrix" # input mixing matrix
    ium="$rawdir/$session/unmixingmatrix" # input unmixing matrix
    iafs="$rawdir/$session/Audio Files/" # input audio files
    
    omm="$datadir/$session/mixingmatrix" # output mixing matrix
    oum="$datadir/$session/unmixingmatrix" # output unmixing matrix
    oafs="$datadir/$session/Audio Files/" # output audio files
    
    # run icapp.py on audio files
    if [ -e "$imm" ] & [ -e "$ium" ]; then
        echo "Using existing ica matrices"
        # previous ica matrices exist, use them
        mkdir -p "$oafs"
        
        cp $imm $omm 
        cp $ium $oum
        
        python $icapp -M $omm -U $oum -o "$oafs" "$iafs"/input_*
    else
        echo "Calculating ica matrices"
        python $icapp -m $icamode -s $icaarg -o "$oafs" "$iafs"/input_*
        echo "copying over ica matrices"

        # safe ica matrices for later use
        cp $omm $imm
        cp $oum $ium
    fi
    # copy over other files
    echo "Copying over auxillary files"
    cp "$iafs"/pixel* "$oafs"
    cp $rawdir/$session/$session.h5 $datadir/$session/
    
    # run analysis
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
