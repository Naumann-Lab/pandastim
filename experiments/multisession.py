import sys
from pathlib import Path

import pandas as pd
from scopeslip import zmqComm
from tifffile import imread

from pandastim import utils
from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus

t_image_path = r"R:/data/matt/2022/3dpf_target_attempt.tif"
t_image = imread(t_image_path)

dparams = (
    Path(sys.executable)
    .parents[0]
    .joinpath(r"Lib\site-packages\pandastim\resources\params\improv_params.json")
)
myWalky = zmqComm.WalkyTalky(
    outputPort="5005", inputIP="tcp://10.122.170.21:", inputPort=4701
)
bud = stimulus_buddies.MultiSessionBuddy(
    walky_talky=myWalky,
    pauseHours=3,
    target_image=t_image,
    savePath=r"C:\data\pstim_stimuli\matt_multisession.txt",
    default_params_path=dparams,
)

inputStimuli = pd.read_hdf(
    Path(sys.executable)
    .parents[0]
    .joinpath(
        r"Lib\site-packages\pandastim\resources\protocols\sevenrep_twentyonestim.hdf"
    )
)

inputStimuli = inputStimuli.loc[:139]  # in this case after 139 is blanks and repeats

# print(inputStimuli)

stimSequence = utils.legacy2current(
    inputStimuli
)  # this converts the saved sequence into stim types

bud.queue = stimSequence

pstim = stimulus.ExternalStimulus(buddy=bud, params_path=dparams)

pstim.run()
