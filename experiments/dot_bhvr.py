#import stimuli.stimulus_details
from pandastim.utils import port_provider, load_params,legacy2current
from pandastim.stimuli import stimulus, stimulus_details
from pandastim.behavior.Protocol import  ClosedLoopProtocol, CenterClickTestingProtocol
from pandastim.behavior.Tracking import stytra_container
from pandastim.buddies.stimulus_buddies import StimulusBuddy, StytraBuddy
from pandastim import utils

import multiprocessing as mp

import sys

from pathlib import Path


parameter_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params\rig_params.json')
stimulus_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\protocols\dot_stim.hdf')

def wrapper(protocol, stimulus_dataframe_path, ports, params, parameter_path):
    """
    :param stimuli:  a stimulus class
    :param stimulus_dataframe_path: path to an hdf that contains stimulus information
    :param ports: ports formatted in a key: port manner for the ports required for bhvr & stim comms
    :param params: json file with all the stuff and the things
    :param parameter_path: the directory of the parameter
    """

    import pandas as pd
    stimulus_dataframe = pd.read_hdf(stimulus_dataframe_path)
    rad_stack = utils.create_radial_sin(texture_size=1024)
    stytraBuddy = StytraBuddy(comms = ports,
                             params_path =parameter_path,
                              protocol = protocol,
                              stimuli = stimulus_dataframe)  # start with pausing until Go, get stytra position output
    pstim = stimulus.BehaviorStimulus(buddy=stytraBuddy, params_path=parameter_path, buddy_port = ports['buddy_stimulus_socket'],
                                      rad_stack=rad_stack)

    pstim.run()

if __name__ == '__main__':

        _ports = {}
        keys = ['image_socket', 'go_socket', 'timing_socket', 'saving_socket', 'tracking_socket',
                'protocol_buddy_socket', 'stimulus_buddy_socket', 'buddy_stimulus_socket']
        for key in keys:
                _ports[key] = str(port_provider())

        params = load_params(parameter_path)

        camera_rot = params['camera_rotation']
        roi = params['roi']
        savedir = params['save_path']

        stytra_process = mp.Process(target=stytra_container, args=(_ports, camera_rot, roi, savedir,))
        stimulus_process = mp.Process(target=wrapper, args=(ClosedLoopProtocol, stimulus_path, _ports, params, parameter_path))


        stimulus_process.start()
        stytra_process.start()

        stytra_process.join()

        if not stytra_process.is_alive():
               stimulus_process.terminate()
               stimulus_process.join()

