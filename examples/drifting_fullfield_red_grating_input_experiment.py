# -*- coding: utf-8 -*-
"""
pandastim/examples/drifting_fullfield_red_grating_input_experiment.py
Example of how to show a drifting grating in an experiment, interspersed with black rgb texture,
toggled with input (in this example, just keyboard)

Note this is not finished, am working on getting it functional.

Part of pandastim package: https://github.com/EricThomson/pandastim
"""
import sys
sys.path.append('..')  #put parent directory in python path

import numpy as np
from pathlib import Path
from os import makedirs
from datetime import datetime
from experiments import FullFieldDriftInputExperiment
from textures import grating_texture_rgb, rgb_texture


#Set up save path
timenow = datetime.now()
now_string = timenow.strftime('%m%d%Y_%H%M%S')
filename = r'experiment_data_' + now_string + '.json'
dir_path = Path(r'./data/')
file_path = dir_path / filename
try:
    makedirs(dir_path)
except FileExistsError:
    print("Storing data in", dir_path, ", which already exists.")

#Set up stimuli
"""
Note we set up texture functions as a dictionary that is passed in, rather than just giving
giving the function direction, so we can encode/save the name and not have to deal with encoding/saving
the function objecty itself (e.g., it is a lazy way to circumvent jsonifying a function object directly)
"""
#stim_params = {'velocity': -0.18, 'spatial_freq': 13, 'angle': -30, 'rgb': (255, 0, 0)}
#texture_size = 512
#window_size = 512
#frame_rate = 50

window_size = 512
spatial_freq = 20
speed = -0.1
angle = -30
frame_rate = 50
texture_size = window_size
# rgb grating and pure color (rgb) are the two textures
texture_functions = {'rgb_grating': grating_texture_rgb,
                     'rgb': rgb_texture}
# Parameters for the texture functions: red rgb_grating, and black full field.
stim_params = [{'texture': 'rgb_grating', 'angle':  angle, 'velocity': speed,
                'kwargs': {'spatial_frequency': spatial_freq, 'texture_size': texture_size, 'rgb': (255,0,0)}},
               {'texture': 'rgb', 'angle': 0, 'velocity': 0,
                'kwargs': {'rgb': (0, 0, 0), 'texture_size': texture_size}},
                                                                          ]
#Arrays of stimulus values and durations
exp_app = FullFieldDriftInputExperiment(stim_params, texture_functions,
                                   window_size = window_size, texture_size = texture_size,
                                   file_path = file_path, profile = True, fps = frame_rate)
#app.plot_timeline()
exp_app.run()