"""
pandastim/examples/open_loop.py

example chaining our two previous examples together and adding binocular stimuli

-a gray sinusoidal texture, set into a moving gray stimulus

-a red sinusoidal texture, set into a moving red stimulus

-a list of these stimuli can be put into an openloop stimulus sequencing stimuli class

-a showbase instance that moves the stimulus according to the stimulusDetails parameters of each

Part of pandastim package: https://github.com/mattdloring/pandastim
"""
from pandastim import utils
from pandastim.stimuli import stimulus, stimulus_details, textures

# create a texture
sin_gray_tex = textures.SinGrayTex(
    texture_size=1024,
    frequency=32,
)
# create a wholefield stimulus with that texture
sin_gray_stimulus = stimulus_details.MonocularStimulusDetails(
    texture=sin_gray_tex,
    angle=33,
    velocity=0.05,
    stationary_time=3,
    duration=8,
    hold_after=6.0,
    stim_name="moving_gray",
)
# create a different texture
sin_red_tex = textures.SinRgbTex(texture_size=1024, frequency=30, color=(255, 0, 0))
# different wholefield stimulus
sin_red_stimulus = stimulus_details.MonocularStimulusDetails(
    texture=sin_red_tex,
    angle=33,
    velocity=-0.05,
    stationary_time=1,
    duration=15,
    stim_name="red_sin",
)

# We can create binocular by combining monocular
combined_binoc_stim = stimulus_details.monocular2binocular(
    sin_gray_stimulus, sin_red_stimulus
)

# or from scratch
grate_gray_tex = textures.GratingGrayTex(texture_size=1024, frequency=32)
fresh_binoc_stim = stimulus_details.BinocularStimulusDetails(
    stim_name="wholefield_right",
    angle=(90, 90),
    velocity=(0.1, 0.1),
    duration=(11, 11),
    stationary_time=(3, 3),
    hold_after=(0.0, 0.0),
    texture=(sin_gray_tex, grate_gray_tex),
)

all_stimuli = [
    sin_gray_stimulus,
    sin_red_stimulus,
    combined_binoc_stim,
    fresh_binoc_stim,
]


pstim = stimulus.OpenLoopStimulus(all_stimuli)

pstim.run()

#%%
