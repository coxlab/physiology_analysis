#!/usr/bin/env python

def listify(func):
    def listified(arg):
        try:
            i = iter(arg)
            return [func(a) for a in i]
        except TypeError:
            return func(arg)
    return listified

@listify
def audio_to_tdt(au):
    return au + 1

@listify
def tdt_to_audio(tdt):
    if tdt == 0:
        raise ValueError("tdt channel 0 does not exist")
    return tdt - 1

@listify
def position_to_tdt(pos):
    return [7,10,1,14,5,12,3,11,2,16,22,15,4,9,18,28,6,13,21,27,8,32,17,31,24,26,20,30,23,25,19,29][pos]

@listify
def tdt_to_position(tdt):
    if tdt == 0:
        raise ValueError("tdt channel 0 does not exist")
    return [-1,2,8,6,12,4,16,0,20,13,1,7,5,17,3,11,9,22,14,30,26,18,10,28,24,29,25,19,15,31,27,23,21][tdt]

@listify
def tdt_to_neuronexus(tdt):
    if tdt == 0:
        raise ValueError("tdt channel 0 does not exist")
    return [-1,2,5,4,7,3,9,1,11,26,32,29,30,24,31,27,28,12,8,16,14,10,6,15,13,18,20,23,25,17,19,21,22][tdt]

@listify
def neuronexus_to_tdt(nn):
    if nn == 0:
        raise ValueError("nn channel 0 does not exists")
    return [-1,7,1,5,3,2,22,4,18,6,21,8,17,24,20,23,19,29,25,30,26,31,32,27,13,28,9,15,16,11,12,14,10][nn]

# no need to listify these
def audio_to_neuronexus(au):
    return tdt_to_neuronexus(audio_to_tdt(au))

def neuronexus_to_audio(nn):
    return tdt_to_audio(neuronexus_to_tdt(nn))

def position_to_audio(pos):
    return tdt_to_audio(position_to_tdt(pos))

def audio_to_position(au):
    return tdt_to_position(audio_to_tdt(au))

def neuronexus_to_position(nn):
    return tdt_to_position(neuronexus_to_tdt(nn))

def position_to_neuronexus(au):
    return tdt_to_neuronexus(position_to_tdt(au))

def test():
    nn = range(1,33)
    tdt = range(1,33)
    pos = range(32)
    audio = range(32)
    
    for n in nn:
        assert tdt_to_neuronexus(neuronexus_to_tdt(n)) == n
        assert audio_to_neuronexus(neuronexus_to_audio(n)) == n
        assert position_to_neuronexus(neuronexus_to_position(n)) == n
    
    for t in tdt:
        assert audio_to_tdt(tdt_to_audio(t)) == t
        assert neuronexus_to_tdt(tdt_to_neuronexus(t)) == t
        assert position_to_tdt(tdt_to_position(t)) == t
    
    for p in pos:
        assert audio_to_position(position_to_audio(p)) == p
        assert tdt_to_position(position_to_tdt(p)) == p
        assert neuronexus_to_position(position_to_neuronexus(p)) == p
    
    for a in audio:
        assert position_to_audio(audio_to_position(a)) == a
        assert neuronexus_to_audio(audio_to_neuronexus(a)) == a
        assert tdt_to_audio(audio_to_tdt(a)) == a
    
    # this is probably enough to test listify
    assert all(tdt_to_neuronexus(neuronexus_to_tdt(nn)))

if __name__ == '__main__':
    test()
    print "Passed test!"