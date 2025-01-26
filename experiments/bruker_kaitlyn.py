import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd
import qdarkstyle
from PyQt5.Qt import QApplication
# from scopeslip import zmqComm
# from scopeslip.gui import alignment_gui
from tifffile import imread

from pandastim import utils
from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus


def pstimWrapper():
    # EDIT your save path here
    mySavePath = r"E:\Kaitlyn\20241216_elavl3rsChrm_H2bg6s_OMR2Stim_6dpf\pstim_output_fish13.txt"

    # parameters necessary for ROI to pop up
    # here you can change the size of the ROI, the rotation of the window, location of window, etc
    # DO NOT CHANGE
    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\default_params.json")
        # .joinpath(r"Lib\site-packages\pandastim\resources\params\behavior_params.json")

    )

    # handles communication with the default parameters necessary to save data
    # DO NOT CHANGE
    stimBuddy = stimulus_buddies.StimulusBuddy(
        reporting="onMotion",
        default_params_path=paramspath,
        outputMethod="zmq",
        savePath=mySavePath,
    )

    inputStimuli = pd.read_hdf(
        Path(sys.executable)
        .parents[0]
        .joinpath(
            # r"Lib\site-packages\pandastim\resources\protocols\sixteenstim.hdf"
            r"Lib\site-packages\pandastim\resources\protocols\all_omr_stims.hdf" # includes shearing stims, faster speeds, randomized each block
            # r"Lib\site-packages\pandastim\resources\protocols\new_stims.hdf"
            # r"Lib\site-packages\pandastim\resources\protocols\twentyonestim_long.hdf"
            # r"Lib\site-packages\pandastim\resources\protocols\twentyonestim_new.hdf"
        )
    )
    # can augment your pstim file here in any way you want
    inputStimuli['freq'] = 70 # NEED TO HAVE A LARGER SPATIAL FREQ FOR SMALLER LINES, before it was 32 freq (maybe getting less responsive neurons)

    intercardinal_dirs = ['forward_left', 'forward_right', 'backward_right', 'backward_left']
    cardinal_dirs =  ['forward', 'left', 'right']
    shearing_stims = ['x_forward', 'backward_forward', 'x_backward', 'backward_x', 'forward_x','forward_backward']

    # 3 REPS OF 14 STIMS AT 25 duration, 1050 sec
    # 4 REPS OF 14 STIMS AT 25 duration, 1400 sec
    # 3 reps of 20 stims at 25 duration, 1500 sec
    # 3 REPS OF 14 STIMS AT 30 duration, 1260 sec
    # 5 REPS OF 14 STIMS AT 30 duration, 2100 sec
    # 3 REPS OF 16 STIMS AT 40 duration, 1920 sec
    # 4 reps of 16 stims at 40 duration, 2560 sec
    # 5 REPS OF 16 STIMS AT 40 duration, 3200 sec
    # 4 REPS OF 14 STIMS AT 30 duration, 1680 sec
    # 3 reps of 14 stims at 40 sec duration, 1680 sec
    # inputStimuli = inputStimuli[:60]
    
    # TEST with cardinal directions to make sure fish is good #
    # inputStimuli = inputStimuli[inputStimuli.stim_name.isin(['forward', 'right', 'left'])].reset_index(drop=True)

    # get rid of specific stims for expt #
    inputStimuli = inputStimuli[~inputStimuli.stim_name.isin(intercardinal_dirs)].reset_index(drop=True)
    # inputStimuli["velocity"] = 0.025
    inputStimuli['stationary_time'] = 30
    inputStimuli['duration'] =  40

    
    # this will generate your stimulus sequence to be sent in the right datastructure
    # DO NOT CHANGE
    stimSequence = utils.generate_stimSequence(inputStimuli)
    stimBuddy.queue = stimSequence
    pstim = stimulus.ExternalStimulus(buddy=stimBuddy, params_path=paramspath)
    pstim.run()


# DO NOT CHANGE
if __name__ == "__main__":

    _processes = [pstimWrapper]

    processes = [mp.Process(target=p) for p in _processes]
    [p.start() for p in processes]
    [p.join() for p in processes]