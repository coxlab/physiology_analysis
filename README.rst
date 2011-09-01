======
Physiology analysis pipeline
======

This is the main analysis pipeline for physiology data collected in the coxlab.

The pipeline (as seen from 1000m) looks like this:

    raw data -> (processing) -> hdf5 session file -> (statistics & visualization) -> results

Configuration
-------------
Most options are configured by creating and editing a .physio file in the users home directory.
This is an ini type file with default settings found in the physio/cfg.py.

Running the pipeline
--------------------

Analyzing a session is as simple as:

    import physio
    physio.analysis.analyze.analyze(session)

where session is in the form of <animal>_<date:yearmonthday> example: K4_110720

This will produce a hdf5 file within the results repository (specified in ~/.physio).

Examining results
-----------------

Opening session results:

    import physio
    mysession = physio.session.Session(resultsfile)

where resultsfile is the path to the hdf5 results file

See physio/session.py for more info.