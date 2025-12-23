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

# if want to run pandastim - need to run separately (new anacomda window and script)

if __name__ == "__main__": #allows the file to be run directly

    #connect to PrairieView
    pl = win32com.client.Dispatch("PrairieLink.Application")

    pl.Connect()
    #print a message if successfully connected
    if(pl.Connected()):
        print("Connected via PrairieLink")
    
    # making save path
    imaging_dir = str('E:/Kaitlyn/troubleshooting/')
    print('save path set')
    pl.SendScriptCommands("-SetSavePath {}".format(imaging_dir))

    ## need to start my imaging here ##
    no_planes = 3
    plane_step = 8
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
        new_z = current_z + plane_step
        pl.SendScriptCommands(f"-SetMotorPosition 'Z' '{new_z}' 'True'")
        pl.SendScriptCommands("-WaitForScan")
        print(f'moved to {new_z} with stack')

    pl.Disconnect()
    print("Disconnected from Prairie View")