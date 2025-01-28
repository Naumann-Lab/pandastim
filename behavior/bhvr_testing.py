from pandastim.behavior import Tracking, Protocol
from pandastim.utils import port_provider, create_radial_sin, load_params
from pandastim.stimuli import BehavioralStimuli

import multiprocessing as mp
import threading as tr

import sys
from pathlib import Path

parameter_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\rig_params.json')
stim_params = load_params(parameter_path)

def stim(_ports, rig=1):
    if stim_params['radial_centering']:
        behavioral_stimuli = BehavioralStimuli(stimuli=None, defaults=stim_params, rad_stack=create_radial_sin(texture_size=stim_params['window_size']))
    else:
        behavioral_stimuli = BehavioralStimuli(stimuli=None, defaults=stim_params, rad_stack=None)

    # the panda3d event handler will not work across processes, but will across threads
    # protocol_thread = tr.Thread(target=Protocol.BaseProtocol, args=(None, _ports, stim_params))
    import pandas as pd

    forward = {
        'stim_name': 'forward',
        'stim_type': 'b',
        'velocity': (0.02, 0.02),
        'angle': (0, 0),
        'center_width': 12,
        'stationary_time': 3,
        'duration': 15,
    }
    backward = {
        'stim_name': 'backward',
        'stim_type': 'b',
        'velocity': (0.02, 0.02),
        'angle': (180, 180),
        'center_width': 12,
        'stationary_time': 3,
        'duration': 15,

    }

    left = {
        'stim_name': 'left',
        'stim_type': 'b',
        'velocity': (0.02, 0.02),
        'angle': (270, 270),
        'center_width': 12,
        'stationary_time': 3,
        'duration': 15,
    }

    stims = pd.DataFrame([forward, backward, left])

    thestimuli = pd.concat([stims] * 5)
    thestimuli.reset_index(inplace=True)

    protocol_thread = tr.Thread(target=Protocol.FishTrackerTestingProtocolB, args=(thestimuli, _ports, stim_params))

    protocol_thread.start()

    behavioral_stimuli.run()

    protocol_thread.join()
    print('joined')


if __name__ == '__main__':

    _ports = {}
    keys = ['image_socket', 'go_socket', 'timing_socket', 'saving_socket', 'tracking_socket']
    for key in keys:
        _ports[key] = str(port_provider())

    print(_ports)

    camera_rot = stim_params['camera_rotation']
    roi = stim_params['roi']
    savedir = stim_params['save_path']
    rig = str(2)

    '''    try:
        from pathlib import Path
        import sys
        basePath = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources')
        json_path = basePath.joinpath('rig' + rig + ".json")

        import json
        with open(json_path, 'r') as json_file:
            params = json.load(json_file)

        roi = params['stytra']['roi']
        print(f'loaded roi as {roi}')
    except Exception as e:
        print('failed to load roi', e)'''


    stytra_process = mp.Process(target=Tracking.stytra_container, args=(_ports, camera_rot, roi, savedir))
    stimuli_process = mp.Process(target=stim, args=(_ports,rig,))

    stytra_process.start()
    stimuli_process.start()

    stytra_process.join()

    if not stytra_process.is_alive():
        stimuli_process.terminate()
        stimuli_process.join()
