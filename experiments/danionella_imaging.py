"""
kaitlyn imaging session with DC larvae
using a pre-saved h5 file containing stim sequence to run an openloop experiment
"""
import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd
import qdarkstyle
from PyQt5.Qt import QApplication
from scopeslip import zmqComm
from scopeslip.gui import alignment_gui

from pandastim import utils
from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus, stimulus_details


def pandastim_wrapper(alignment_comms):
    # you could change this to do the saving and the stuff
    save_path = None

    # params path,
    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\improv_params.json")
    )

    # start up our lil buddy and have him report when textures start moving

    stimBuddy = stimulus_buddies.AligningStimBuddy(
        reporting="onMotion",
        alignmentComms=alignment_comms,
        default_params_path=paramspath,
        outputMethod="zmq",
        savePath=save_path,
    )

    # this uses stimulusBuddy to run open loop experiments
    inputStimuli = pd.read_hdf(
        Path(sys.executable)
        .parents[0]
        .joinpath(
            r"Lib\site-packages\pandastim\resources\protocols\sevenrep_17stim.hdf"
        )
    )

    # inputStimuli = inputStimuli.loc[:139]  # in this case after 139 is blanks and repeats
    stimSequence = utils.legacy2current(
        inputStimuli
    )  # this converts the saved sequence into stim types

    stimBuddy.queue = stimSequence  # add our stims into the queue

    pstim = stimulus.ExternalStimulus(buddy=stimBuddy, params_path=paramspath)

    pstim.run()


def alignment_wrapper(alignment_comms):
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    # handles communication with labview
    myWalky = zmqComm.WalkyTalky(
        outputPort="5005", inputIP="tcp://10.122.170.21:", inputPort="4701"
    )

    pa = alignment_gui.PlaneAligner(
        walkytalky=myWalky,
        stimBuddyPorts=alignment_comms,
    )
    pa.show()
    app.exec()


if __name__ == "__main__":

    alignment_communication_ports = {"wt_output": "5015", "wt_input": "5016"}

    _processes = [pandastim_wrapper, alignment_wrapper]

    processes = [
        mp.Process(target=p, args=(alignment_communication_ports,)) for p in _processes
    ]
    [p.start() for p in processes]
    [p.join() for p in processes]
