# -*- coding: utf-8 -*-
"""
pandastim/examples/static_binocular_grating.py
Example of how to present a static binocular grating.

Part of pandastim package: https://github.com/EricThomson/pandastim 
"""
import sys
sys.path.append('..')  #put parent directory in python path

from stimulus_classes import BinocularStatic
from textures import grating_texture

stim_params = {'spatial_freq': 20, 'stim_angles': (30, -30), 
               'position': (0, 0), 'band_radius': 1}
mask_angle = 45  #this will change frequently in practice so not in dict
texture_size = 512
window_size = 512  
texture = grating_texture(texture_size, stim_params['spatial_freq'])
binocular_static = BinocularStatic(texture, 
                                   stim_angles = stim_params["stim_angles"],
                                   mask_angle = mask_angle,
                                   position = stim_params["position"], 
                                   band_radius = stim_params['band_radius'],
                                   window_size = window_size,
                                   texture_size = texture_size)
binocular_static.run()