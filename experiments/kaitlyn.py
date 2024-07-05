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
    mySavePath = r"C:\data\kaitlyn\pstim_output.txt"
    # mySavePath = None
    # handles communication from improv
    pstim_comms = {"topic": "stim", "port": "5006", "ip": r"tcp://10.122.170.169:"}
    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\improv_params.json")
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
    # fourstim_speed is 4 directions, whole field (s), 0.01, 0.02, 0.04 mm/s velocities for each one
    inputStimuli = pd.read_hdf(
        Path(sys.executable)
        .parents[0]
        .joinpath(
            r"Lib\site-packages\pandastim\resources\protocols\fourstim_speed.hdf"
        )
    )
    # # sixteen directions at the same speed and duration
    # inputStimuli = inputStimuli.loc[:139]
    #
    # ## drop the forward back nonsense ##
    # badList = [
    #     "x_forward",
    #     "forward_x",
    #     "x_backward",
    #     "backward_x",
    #     "backward_forward",
    #     "forward_backward",
    # ]
    # inputStimuli = inputStimuli[~inputStimuli.stim_name.isin(badList)]
    # inputStimuli.reset_index(drop=True, inplace=True)
    # inputStimuli = pd.concat([inputStimuli] * 3).reset_index(drop=True)

    stimSequence = utils.legacy2current(inputStimuli)
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

    _processes = [pstimWrapper, alignmentWrapper]

    processes = [mp.Process(target=p, args=(alignment_ports,)) for p in _processes]
    [p.start() for p in processes]
    [p.join() for p in processes]
