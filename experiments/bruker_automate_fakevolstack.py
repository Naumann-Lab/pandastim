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

import win32com.client
import numpy as np
import socket
import os
from time import sleep

from bruker_control.main import prairieview_utils


def pstimWrapper(pstim_save_path):    
    # parameters necessary for ROI to pop up
    # here you can change the size of the ROI, the rotation of the window, location of window, etc
    paramspath = (
        Path(sys.executable)
        .parents[0]
        .joinpath(r"Lib\site-packages\pandastim\resources\params\default_params.json")
    )

    # handles communication with the default parameters necessary to save data
    stimBuddy = stimulus_buddies.StimulusBuddy(
        reporting="onMotion",
        default_params_path=paramspath,
        outputMethod="zmq",
        savePath=pstim_save_path,
    )

    # this uses stimulusBuddy to run open loop experiments
    inputStimuli = pd.read_hdf(
        Path(sys.executable)
        .parents[0]
        .joinpath(
            r"Lib\site-packages\pandastim\resources\protocols\twentyonestim_new.hdf"
        )
    )
    # can augment your pstim file here in any way you want
    inputStimuli = inputStimuli.loc[:1]

    # this will generate your stimulus sequence to be sent in the right datastructure
    stimSequence = utils.generate_stimSequence(inputStimuli)
    stimBuddy.queue = stimSequence
    pstim = stimulus.ExternalStimulus(buddy=stimBuddy, params_path=paramspath)
    pstim.run()

if __name__ == "__main__": #allows the file to be run directly

    #connect to PrairieView
    pl = win32com.client.Dispatch("PrairieLink.Application")

    pl.Connect()
    #print a message if successfully connected
    if(pl.Connected()):
        print("Connected via PrairieLink")
    
    # making save path
    imaging_dir = str('E:/Kaitlyn/automation_testing/')
    print('save path set')
    pl.SendScriptCommands("-SetSavePath {}".format(imaging_dir))

    ## need to start my imaging here ##
    no_planes = 3
    for n in range(no_planes):
        current_z = pl.GetMotorPosition("Z")        
        imaging_filename = str(f'plane_{n}')
        print(imaging_filename)
        pl.SendScriptCommands("-SetFileName Tseries {}".format(imaging_filename))

        print(f'starting t series for plane {n}, current z is {current_z}')
        pl.SendScriptCommands("-TSeries") # current t-series set up
        pl.SendScriptCommands("-WaitForScan")
        print('scan done')

        # changing z
        new_z = current_z + 5
        pl.SendScriptCommands(f"-SetMotorPosition 'Z' '{new_z}' 'True'")
        pl.SendScriptCommands("-WaitForScan")
        print(f'moved to {new_z} with stack')

    pl.Disconnect()
    print("Disconnected from Prairie View")