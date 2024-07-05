import multiprocessing as mp
import sys
from pathlib import Path

import qdarkstyle
from PyQt5.Qt import QApplication
from scopeslip import zmqComm
from scopeslip.gui import alignment_gui

from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus, stimulus_details


def pandastim_wrapper(alignment_comms):
    # handles communication from improv
    pstim_comms = {"topic": "stim", "port": "5006", "ip": r"tcp://10.122.170.169:"}

    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\improv_params.json")
    )

    stimulus_buddy = stimulus_buddies.AligningStimBuddy(
        reporting="onMotion",
        pstim_comms=pstim_comms,
        alignmentComms=alignment_comms,
        default_params_path=paramspath,
        outputMethod="zmq",
    )

    pstim = stimulus.ExternalStimulus(buddy=stimulus_buddy, params_path=paramspath)
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
