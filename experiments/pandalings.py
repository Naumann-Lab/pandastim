#import stimuli.stimulus_details
from pandastim.utils import port_provider, load_params,legacy2current
from pandastim.stimuli import  stimulus_details
from pandastim.improv.improv_protocol import  TailLockedProtocol
from pandastim.improv.improv_tracking import stytra_container
from pandastim.improv.improv_buddy import BrukerBuddy
from pandastim.improv import improv_stimulus

from pandastim import utils

import multiprocessing as mp
import pandas as pd
import sys
from pathlib import Path
import subprocess


parameter_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params\rig_params.json')

def wrapper(protocol, ports, parameter_path):
    """
    :param stimuli:  a stimulus class
    :param stimulus_dataframe_path: path to an hdf that contains stimulus information
    :param ports: ports formatted in a key: port manner for the ports required for bhvr & stim comms
    :param params: json file with all the stuff and the things
    :param parameter_path: the directory of the parameter
    """


    #rad_stack = utils.create_radial_sin(texture_size=1024)
    stytraBuddy = BrukerBuddy(comms = ports,
                             params_path =parameter_path,
                              protocol = protocol)  # start with pausing until Go, get stytra position output
    pstim = improv_stimulus.TailLockedStimulus(buddy=stytraBuddy, params_path=parameter_path) #, buddy = ports['buddy_stimulus_socket'])

    pstim.run()


if __name__ == '__main__':

        _ports = {}
        keys = ['image_socket', 'go_socket', 'timing_socket', 'saving_socket', 'tracking_socket',
                'protocol_buddy_socket', 'stimulus_buddy_socket', 'buddy_stimulus_socket', 'buddy_protocol_socket', 
                "improv_protocol_socket"]
        for key in keys:
                _ports[key] = str(port_provider())

        params = load_params(parameter_path)

        camera_rot = params['camera_rotation']
        roi = params['roi']
        savedir = params['save_path']

        # IMPROV PLACEHOLDER:


        subprocess.Popen([
               "python",
               r"C:\Users\User\anaconda3\envs\pstim_cd\Lib\site-packages\pandastim\improv\improv_placeholder.py",
               _ports["improv_protocol_socket"]  #I WILL DECIDE LATER IF I WANT TO CHANGE THIS TO ONLY TAKE THE ACTUAL IMPROV PORT OR IF IT WILL HAVE TO HANDLE MULTIPLE SOCKETS
        ])


        ###

        stytra_process = mp.Process(target=stytra_container, args=(_ports, camera_rot, roi, savedir,))
        if params['pstim']:
               stimulus_process = mp.Process(target=wrapper, args=(TailLockedProtocol, _ports, parameter_path))
               stimulus_process.start()
        stytra_process.start()
        stytra_process.join()
        if params['pstim']:
                if not stytra_process.is_alive():
                        stimulus_process.terminate()
                        stimulus_process.join()
