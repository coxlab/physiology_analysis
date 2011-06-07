import os
import re

def cleanup_audio_filenames( path ):

    files = os.listdir( os.path.join(path, "Audio Files") )
    filt_files = filter( lambda x: x.find("Input ") == 0, files )
    
    for f in filt_files:
        matches = re.match(r"Input\s(\d+)#(\d+)", f)
        channel_number = int(matches.group(1))
        session_number = int(matches.group(2))
        new_filename = "input_%d#%.2d.wav" % (channel_number, session_number)
        
        old_full_path = os.path.join(path, "Audio Files", f)
        new_full_path = os.path.join(path, "Audio Files", new_filename)
        
        print("%s -> %s" % (old_full_path, new_full_path))
        os.rename( old_full_path, new_full_path )