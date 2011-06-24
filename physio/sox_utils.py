import os
import re
import subprocess
import shlex
import tempfile

def to_hms(seconds):
    hours = int(seconds / 3600.)
    seconds -= 3600. * hours
    minutes = int(seconds / 60.)
    seconds -= 60. * minutes
    return "%02d:%02d:%.2f" % (hours, minutes, seconds)

    
# def sox_merge(stem, session_number, project_path, out_path, out_filename,
#               time_range = None, sinc_bandpass = None, bandpass = None,
#               highpass = None, norm = False, format="wavpcm", tmp_path=None):
def sox_merge(stem, project_path, out_filename,
              time_range = None, sinc_bandpass = None, bandpass = None,
              highpass = None, norm = False, format="wavpcm", tmp_dir=None):
    """
    Session number is NOT used
    """
    
    # matchstring = r"%s_?\d+#%.2d.wav" % (stem, session_number)
    matchstring = r"%s_?\d+#\d..wav" % stem
    
    if tmp_dir == None:
        tmp_dir = os.path.join(os.path.dirname(out_filename), "tmp")
    
    # out_file_path = os.path.join(out_path, out_filename)
    if not (os.path.exists(tmp_dir)): os.makedirs(tmp_dir)
    # if not (os.path.exists(out_path)): os.makedirs(out_path)
    #subprocess.check_call(["mkdir", "-p", tmp_path])
    #subprocess.check_call(["mkdir", "-p", out_path])
    
    
    merge_command_template = "sox --temp %s -M %s -t %s %s"
    per_channel_command_template = "sox --temp %s %s -t wavpcm %s"
    
    if time_range is not None:
        
        (begin_time, end_time) = time_range
            
        time_length = end_time - begin_time
        print("Time length = %f" % time_length)
        per_channel_command_template += " trim %s %s" % (to_hms(begin_time), to_hms(time_length))
    
    if sinc_bandpass is not None:
        (low, high) = sinc_bandpass
        per_channel_command_template += " sinc -M %d-%d" % (low, high)
    
    if bandpass is not None:
        (center, width) = bandpass
        if center > 1000.:
            center_string = "%fk" % (center / 1000.)
        else: 
            center_string = "%f" % center

        if width > 1000.:
            width_string = "%fk" % (width / 1000.)
        else:
            width_string = "%f" % width
            
        per_channel_command_template += " band %s %s" % (center_string, width_string)
    
    if highpass is not None:
        #command_template += " highpass %d" % high_cut
        per_channel_command_template += " sinc -M %d-200" % highpass
    
    if norm:
        per_channel_command_template += " gain -e -n"
    
    audio_file_path = os.path.join(project_path, "Audio Files")
    audio_files = os.listdir(audio_file_path)
    
    filtered_files = filter(lambda x: bool(re.match(matchstring, x)), audio_files)
    
    def extract_channel_num(s):
        print s
        m = re.match(r"%s_?(\d+)#.*"%stem, s)
        return int(m.group(1))
    
    filtered_files.sort(key=extract_channel_num)
    
    
    # generate a unique temp dir to store per-channel processed files
    #per_channel_tmp_dir = tempfile.mkdtemp("", tmp_path)
    per_channel_tmp_dir = tmp_dir
    
    qq = lambda x: '"' + x + '"'
    
    # process each per-channel sox command
    for ff in filtered_files:
        ff_input_path = os.path.join(audio_file_path, ff)
        ff_output_path = os.path.join(per_channel_tmp_dir, ff)
        per_channel_cmd = per_channel_command_template % (tmp_dir,
                                                          qq(ff_input_path),
                                                          qq(ff_output_path))
        print("Processing individual channel file: %s" % ff)
        print("\t%s" % per_channel_cmd)
        subprocess.check_call(shlex.split(per_channel_cmd))
        
    
    
    full_paths = ['"' + os.path.join(per_channel_tmp_dir, x) + '"' 
                                                    for x in filtered_files]
    
    
    full_merge_command = merge_command_template % (tmp_dir, 
                                                   " ".join(full_paths), 
                                                   format, 
                                                   out_filename)
    
    print("Running sox command: \n\t%s" % full_merge_command)
    

    subprocess.check_call(shlex.split(full_merge_command))
    
        
    return out_filename
