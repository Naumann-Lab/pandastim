import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd
import qdarkstyle
from PyQt5.Qt import QApplication
from scopeslip import zmqComm
from scopeslip.gui import bruker_crosscorrelation_flexphotostim
from tifffile import imread

from pandastim import utils
from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus


def pstimWrapper(alignmentPorts):
    # EDIT your save path here
    mySavePath = r"E:\Kaitlyn\pstim_output.txt"

    # parameters necessary for ROI to pop up
    # here you can change the size of the ROI, the rotation of the window, location of window, etc
    # DO NOT CHANGE
    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\default_params.json") # most updated in jan 2025
    )

    # handles communication with gui
    pstim_comms = {"topic": "stim", "port": "5006", "ip": r"tcp://10.122.170.169:"}
    # pstim_comms = {"pstim_output": "5010", "pstim_input": "5006"}

    stimBuddy = stimulus_buddies.AligningStimBuddy(
        reporting="onMotion",
        pstim_comms=pstim_comms,
        alignmentComms=alignmentPorts,
        default_params_path=paramspath,
        outputMethod="zmq",
        savePath=mySavePath,)
    
# all omr stims file includes shearing stims, faster speeds, randomized each block
    # inputStimuli = pd.read_hdf(
    #     Path(sys.executable)
    #     .parents[0]
    #     .joinpath(r"Lib\site-packages\pandastim\resources\protocols\all_omr_stims_aug2025_newvel.hdf" ))
    

    # # can augment your pstim file here in any way you want
    # inputStimuli['freq'] = 60 # NEED TO HAVE A LARGER SPATIAL FREQ FOR SMALLER LINES, before it was 32 freq (maybe getting less responsive neurons)

    # intercardinal_dirs = ['forward_left', 'forward_right', 'backward_right', 'backward_left']
    # cardinal_dirs =  ['forward', 'left', 'right', 'backward']
    # shearing_stims = ['x_forward', 'backward_forward', 'x_backward', 'backward_x', 'forward_x','forward_backward']

    # # 3 reps of 16 stims at 15 duration, 720 sec

    # # 3 REPS OF 14 STIMS AT 25 duration, 1050 sec
    # # 4 REPS OF 14 STIMS AT 25 duration, 1400 sec
    # # 3 REPS OF 16 STIMS AT 25 duration, 1200 sec
    # # 3 reps of 20 stims at 25 duration, 1500 sec
    # # 4 reps of 20 stims at 25 duration, 2000 sec

    # # 3 REPS OF 14 STIMS AT 30 duration, 1260 sec
    # # 5 REPS OF 14 STIMS AT 30 duration, 2100 sec
    # # 4 REPS OF 16 STIMS AT 30 duration, 1920 sec
    # # 4 REPS OF 14 STIMS AT 30 duration, 1680 sec

    # # 3 reps of 20 stims at 40 duration, 2400 sec
    # # 3 REPS OF 16 STIMS AT 40 duration, 1920 sec
    # # 4 reps of 16 stims at 40 duration, 2560 sec
    # # 5 REPS OF 16 STIMS AT 40 duration, 3200 seac
    # # 3 reps of 14 stims at 40 sec duration, 1680 sec
    # # 4 reps of 11 stims at 40 sec duration, 1760 sec
    # #     
    # # TEST if fish is centered
    # inputStimuli['stationary_time'] = 20
    # inputStimuli['duration'] =  25


    # # # TEST with cardinal directions to make sure fish is good #
    # # inputStimuli = inputStimuli[inputStimuli.stim_name.isin(['forward', 'right', 'left'])].reset_index(drop=True)

    # # get rid of specific stims for expt #
    
    # # inputStimuli = inputStimuli[~inputStimuli.stim_name.isin(shearing_stims)].reset_index(drop=True)
    # inputStimuli = inputStimuli[~inputStimuli.stim_name.isin(intercardinal_dirs)].reset_index(drop=True)
    # # inputStimuli = inputStimuli[inputStimuli.stim_name.isin(['forward', 'backward_left', 'backward_right'])].reset_index(drop=True)
    # # inputStimuli['stationary_time'] = 3
    # # inputStimuli['duration'] =  5
    
    # # this will generate your stimulus sequence to be sent in the right datastructure
    # # DO NOT CHANGE
    # stimSequence = utils.generate_stimSequence(inputStimuli)
    # stimBuddy.queue = stimSequence


    pstim = stimulus.ExternalStimulus(buddy=stimBuddy, params_path=paramspath)
    pstim.run()



# DO NOT CHANGE
if __name__ == "__main__":

    alignment_ports = {"wt_output": "5015", "wt_input": "5016"}

    _processes = [pstimWrapper]

    processes = [mp.Process(target=p, args=(alignment_ports,)) for p in _processes]
    [p.start() for p in processes]
    [p.join() for p in processes]