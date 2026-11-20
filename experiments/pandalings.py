#import stimuli.stimulus_details
from pandastim.utils import port_provider, load_params,legacy2current
from pandastim.stimuli import  stimulus_details
from pandastim.improv.improv_protocol import  TailLockedProtocol, OpenLoopProtocol
from pandastim.improv.improv_tracking import stytra_container
from pandastim.improv.improv_buddy import BrukerBuddy, StimulusBuddy
from pandastim.improv import improv_stimulus

from pandastim import utils

import multiprocessing as mp
import pandas as pd
import sys
from pathlib import Path
import subprocess
import argparse

parameter_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params\rig_params.json')

def wrapper(protocol, ports, parameter_path, tail_arg):
        """
        :param stimuli:  a stimulus class
        :param stimulus_dataframe_path: path to an hdf that contains stimulus information
        :param ports: ports formatted in a key: port manner for the ports required for bhvr & stim comms
        :param params: json file with all the stuff and the things
        :param parameter_path: the directory of the parameter
        :param tail_arg: parsed argument from CLI entry TRUE if user includes flag -t or --tail
        """

        if tail_arg:
                #rad_stack = utils.create_radial_sin(texture_size=1024)
                stytraBuddy = BrukerBuddy(comms = ports,
                                        params_path =parameter_path,
                                        protocol = protocol)  # start with pausing until Go, get stytra position output
                pstim = improv_stimulus.TailLockedStimulus(buddy=stytraBuddy, params_path=parameter_path) #, buddy = ports['buddy_stimulus_socket'])

                pstim.run()
        else:
                stimBuddy = StimulusBuddy(comms = ports,
                                        default_params_path =parameter_path, # CBD note:  I recognize that these are different naming conventions.  this seems estigial from a naming disagreement between ZH and ML branches
                                        protocol = protocol)  # start with pausing until Go, get stytra position output
                pstim = improv_stimulus.SequencingWithPause(buddy=stimBuddy, params_path=parameter_path) #, buddy = ports['buddy_stimulus_socket'])

                pstim.run()



if __name__ == '__main__':
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tail", action="store_true")
        args = parser.parse_args()

        _ports = {}
        keys = ['image_socket', 'go_socket', 'timing_socket', 'saving_socket', 
                'protocol_buddy_socket', 'stimulus_buddy_socket', 'buddy_stimulus_socket', 'buddy_protocol_socket', 
                "improv_protocol_socket"]

        if args.tail:
               keys.append('tracking_socket')

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
               _ports["improv_protocol_socket"] 
        ])


        ###
        if args.tail:
                stytra_process = mp.Process(target=stytra_container, args=(_ports, camera_rot, roi, savedir,))
                if params['pstim']:
                        stimulus_process = mp.Process(target=wrapper, args=(TailLockedProtocol, _ports, parameter_path, args.tail))
                        stimulus_process.start()
                stytra_process.start()
                stytra_process.join()
                if params['pstim']:
                        if not stytra_process.is_alive():
                                stimulus_process.terminate()
                                stimulus_process.join()
        else:
                if params['pstim']:
                        stimulus_process = mp.Process(target=wrapper, args=(OpenLoopProtocol, _ports, parameter_path, args.tail))
                        stimulus_process.start()
