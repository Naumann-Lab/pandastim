import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd
import qdarkstyle
from PyQt5.Qt import QApplication
from scopeslip import zmqComm
from scopeslip.gui import alignment_gui
from tifffile import imread

from pandastim import utils
from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus


def pstimWrapper():
    # EDIT your save path here
    mySavePath = r"E:\Elysia\test.txt"

    # parameters necessary for ROI to pop up
    # here you can change the size of the ROI, the rotation of the window, location of window, etc
    # DO NOT CHANGE
    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\default_params.json")
    )

    # handles communication with the default parameters necessary to save data
    # DO NOT CHANGE
    stimBuddy = stimulus_buddies.StimulusBuddy(
        reporting="onMotion",
        default_params_path=paramspath,
        outputMethod="zmq",
        savePath=mySavePath,
    )

    # this uses stimulusBuddy to run open loop experiments
    # EDIT wtih your hdf file
    inputStimuli = pd.read_hdf(
        Path(sys.executable)
        .parents[0]
        .joinpath(
            # r"Lib\site-packages\pandastim\resources\protocols\twentyonestim_new.hdf"
            r"Lib\site-packages\pandastim\resources\protocols\elysia_stims.hdf"
        )
    )
    # can augment your pstim file here in any way you want
    inputStimuli = inputStimuli.loc[:10]

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