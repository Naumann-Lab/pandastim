"""
pandastim/examples/openloop_stimbuddy.py

example using a pre-saved h5 file containing stim sequence to run an openloop experiment

Part of pandastim package: https://github.com/mattdloring/pandastim
"""
import sys
from pathlib import Path

import pandas as pd

from pandastim import utils
from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus, stimulus_details

save_path = None  # you could change this to do the saving and the stuff

# start up our lil buddy and have him report when textures start moving
stimBuddy = stimulus_buddies.StimulusBuddy(
    reporting="onMotion", outputMethod="print", savePath=save_path
)

# this uses stimulusBuddy to run open loop experiments
inputStimuli = pd.read_hdf(
    Path(sys.executable)
    .parents[0]
    .joinpath(
        r"Lib\site-packages\pandastim\resources\protocols\sevenrep_twentyonestim.hdf"
    )
)

inputStimuli = inputStimuli.loc[:139]  # in this case after 139 is blanks and repeats
stimSequence = utils.legacy2current(
    inputStimuli
)  # this converts the saved sequence into stim types

stimBuddy.queue = stimSequence  # add our stims into the queue

pstim = stimulus.ExternalStimulus(buddy=stimBuddy)

pstim.run()
