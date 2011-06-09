import sox_utils
import sys
import os
import sox_utils
import subprocess
import shlex
import tables
import numpy

from caton.core import classify_from_raw_data

TDT_PADS = [6,9,0,13,4,11,2,10,1,15,21,14,3,8,17,27,5,12,20,26,7,31,16,30,23,25,19,29,22,24,18,28]

def generate_probe_file( pad_sequence, out_filename ):
    
    out_string = ""
    
    for (i, d) in zip(pad_sequence, xrange(len(pad_sequence))):
        out_string += "CH%d %d (%d)\n" % (i, i, d)
    # for i in range(0, len(pad_sequence)):
    #     out_string += "CH%d %d (%d)\n" % (i, i, pad_sequence[i])
    
    f = open(out_filename, 'w')
    f.writelines(out_string)
    f.close()

def generate_shell_xml_file( out_filename ):
    
    content = """<?xml version = '1.0'?>
        <root>
         <acquisitionSystem>
          <nBits>16</nBits>
          <nChannels>32</nChannels>
          <samplingRate>44100</samplingRate>
          <voltageRange>1</voltageRange>
          <amplification>10000</amplification>
          <offset>0</offset>
         </acquisitionSystem>
        </root>
    """ 
    f = open(out_filename, 'w')
    f.writelines(content)
    f.close()
   
def convert_audio_to_caton_format( base_path, session_number, **kwargs):
    
    tr = kwargs.get("time_range", None)
    
    output_path = os.path.join(base_path, "processed")
    
    try:
        os.makedir(output_path)
    except:
        pass
        
    out_filename = "session_%d_%d_to_%d.dat" % (session_number, int(tr[0]), int(tr[1]))    
    dat_file = sox_utils.sox_merge("input_", session_number, base_path, 
                                   output_path, out_filename,
                                   format="s16", norm=True,
                                   time_range=tr,
                                   sinc_bandpass=(500, 3000))

def caton_cluster_data( base_path, session_number, **kwargs ):
    
    time_range = kwargs.get("time_range", None)
    
    # check if the data has been converted already, if not convert it
    processed_path = os.path.join(base_path, "processed")
    dat_path = os.path.join(processed_path, "session_%d_%d_to_%d.dat" % \
                                (session_number, int(time_range[0]), int(time_range[1])))
    if not os.path.exists(dat_path):
        convert_audio_to_caton_format( base_path, session_number, 
                                       **kwargs )
    
    # generate a probe file
    probe_path = os.path.join(processed_path, "a32.probe")
    # generate_probe_file(range(0,32), probe_path)
    generate_probe_file(TDT_PADS, probe_path)
    
    # generate an XML file for caton
    generate_shell_xml_file(os.path.join(processed_path, \
                                         "session_%d_%d_to_%d.xml" % \
                                         (session_number, int(time_range[0]), int(time_range[1]))))
    
    
    classify_from_raw_data("batch", dat_path, probe_path, output_dir=processed_path)
    # prepare the caton command
    #command = "/myPython/bin/cluster_from_raw_data.py %s --probe=%s" % \
    #                        (dat_path, os.path.join(processed_path,"a32.probe"))
    #os.chdir(processed_path)
    #print(command)
    #subprocess.check_call(shlex.split(command))

def str_to_seconds(time_string):
    (hours, minutes, seconds) = time_string.split(":")
    return 3600 * int(hours) + 60 * int(minutes) + float(seconds)

def example_waveforms(clusters, waveforms, n = 0):
    examples = []
    
    for i in range( min(clusters), max(clusters)):
        for c in range(0, len(clusters)):
            if clusters[c] == i:
                examples.append(waveforms[c])
                break
    return examples

def example_waveforms_one_channel(clusters, waveforms, triggers):
    examples = []
    channels = []

    for i in range( min(clusters), max(clusters)):
        for c in range(0, len(clusters)):
            if clusters[c] == i:
                trigger_profile = triggers[c]
                trigger_channel = numpy.argsort(trigger_profile)[-1]
                examples.append(waveforms[c][:, trigger_channel])
                channels.append(trigger_channel)
                break
    return (examples, channels)


def waveform_on_channel(clusters, waveforms, n, ch):
    
    examples = []
    for c in range(0, len(clusters)):
        if clusters[c] == n:
            examples.append(waveforms[c][:,ch])
            
    return examples

def extract_info_from_h5(h5_filename):
    
    f = tables.openFile(h5_filename)
    spike_table = f.root.SpikeTable
    
    clusters = [ x["clu"] for x in spike_table.iterrows()]
    times = [ x["time"] for x in spike_table.iterrows()]
    triggers = [ x["st"] for x in spike_table.iterrows()]
    waveforms = [ x["wave"] for x in spike_table.iterrows()]

    return (clusters, times, triggers, waveforms)

def spikes_by_cluster(times, clusters):
    spike_trains = []
    float_times = numpy.array([t / 44100. for t in times])
    clusters_array = numpy.array(clusters)
    for i in range(min(clusters), max(clusters)):
        spike_trains.append(float_times[clusters_array == i])
    
    return spike_trains

def spikes_by_channel(times, triggers):
    spike_trains = []
    float_times = numpy.array([t / 44100. for t in times])
    tr_ch = [ numpy.argsort(tr)[-1] for tr in triggers]
    for ch in numpy.unique(tr_ch):
        spike_trains.append(float_times[tr_ch == ch])
    
    return spike_trains
    
if __name__ == "__main__":
    
    base_path = sys.argv[1]
    sesion_number = int(sys.argv[2])
    if len(sys.argv) > 4:
        begin_time = sys.argv[3]
        end_time = sys.argv[4]
        
        if begin_time.find(":") > 0:
            begin_time = str_to_seconds(begin_time)
        if end_time.find(":") > 0:
            end_time = str_to_seconds(end_time)
        
        tr = ( float(begin_time), float(end_time) )
    else:
        tr = None
        
    caton_cluster_data(sys.argv[1], int(sys.argv[2]), time_range=tr)
