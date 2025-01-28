from pandastim.behavior import Tracking, Protocol
from pandastim.utils import port_provider, create_radial_sin
from pandastim.stimuli import BehavioralStimuli, Behavior

import multiprocessing as mp
import threading as tr

stim_params = {
    'light_value' : 255,
    'dark_value' : 0,
    'frequency' : 32,
    'center_width' : 16,
    'strip_angle' : 0,
    'center_x' : 0,
    'center_y' : 0,
    'scale' : 8,
    'rotation_offset' : -90,
    'center_dot_size' : 25,
    'center_coord' : (484, 522),
    'window_size' : (1024, 1024),
    'window_position' : (4352, 0),
    'min_fish_dst_to_center' : 250,
    'missing_fish_t' : 0.2,
    'radial_centering' : True,
    'fps' : 60,
    'window_undecorated' : True,
    'window_foreground' : True,
    'window_title' : 'Pandastim',
    'profile_on' : False,
    'projecting_fish' : True,
    'save_path' : r'C:\Users\matt\Data\refactor_test1\four_dpf',
    'rig_number' : 2

}


def stimulus(_ports, rig=1):
    behavioral_stimuli = Behavior(stimuli=None, defaults=stim_params, rad_stack=None)
    protocol_thread = tr.Thread(target=Protocol.CenterClickTestingProtocol, args=(None, _ports, stim_params))

    protocol_thread.start()

    behavioral_stimuli.run()

    protocol_thread.join()


if __name__ == '__main__':

    _ports = {}
    keys = ['image_socket', 'go_socket', 'timing_socket', 'saving_socket', 'tracking_socket']
    for key in keys:
        _ports[key] = str(port_provider())

    print(_ports)

    camera_rot = -1
    roi = None
    savedir = stim_params['save_path']
    rig = str(2)

    try:
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
        print('failed to load roi', e)


    stytra_process = mp.Process(target=Tracking.stytra_container, args=(_ports, camera_rot, roi, savedir))
    stimuli_process = mp.Process(target=stimulus, args=(_ports, rig,))

    stytra_process.start()
    stimuli_process.start()

    stytra_process.join()

    if not stytra_process.is_alive():
        stimuli_process.terminate()
        stimuli_process.join()
