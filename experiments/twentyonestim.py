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


def pstimWrapper(alignmentPorts):
    mySavePath = r"E:\Pstim\test_output.txt"

    # handles communication from improv
    pstim_comms = {"topic": "stim", "port": "5006", "ip": r"tcp://10.122.170.169:"}
    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\default_params.json")
    )
    # handles communication with alignment gui
    stimBuddy = stimulus_buddies.AligningStimBuddy(
        reporting="onMotion",
        pstim_comms=pstim_comms,
        alignmentComms=alignmentPorts,
        default_params_path=paramspath,
        outputMethod="zmq",
        savePath=mySavePath,
    )
    # this uses stimulusBuddy to run open loop experiments
    inputStimuli = pd.read_hdf(
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\protocols\medial_right.hdf"
            # r"Lib\site-packages\pandastim\resources\protocols\sevenrep_twentyonestim.hdf" 
        )
    )
    # can augment your pstim file here in any way you want
    #inputStimuli = inputStimuli.loc[:139]

    # set duration and stationary time here
    stimSequence = utils.legacy2current(inputStimuli, duration=100000, stationary_time=5)
    stimBuddy.queue = stimSequence

    pstim = stimulus.ExternalStimulus(buddy=stimBuddy, params_path=paramspath)

    pstim.run()


def alignmentWrapper(alignmentPort):
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    # handles communication with labview
    myWalky = zmqComm.WalkyTalky(
        outputPort="5005", inputIP="tcp://10.122.170.21:", inputPort="4701"
    )
    pa = alignment_gui.PlaneAligner(
        walkytalky=myWalky, stimBuddyPorts=alignmentPort, resetMode=False
    )
    pa.show()
    app.exec()


if __name__ == "__main__":

    alignment_ports = {"wt_output": "5015", "wt_input": "5016"}

    _processes = [pstimWrapper]
    #_processes = [pstimWrapper, alignmentWrapper]

    processes = [mp.Process(target=p, args=(alignment_ports,)) for p in _processes]
    [p.start() for p in processes]
    [p.join() for p in processes]
