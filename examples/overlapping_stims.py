"""
pandastim/examples/openloop_stimbuddy.py

example using a pre-saved h5 file containing stim sequence to run an openloop experiment

Part of pandastim package: https://github.com/mattdloring/pandastim
"""
from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus, stimulus_details, textures

save_path = None  # you could change this to do the saving and the stuff
params = r'C:\Users\Naumann_Lab\Miniconda3\envs\rig5c\Lib\site-packages\pandastim\resources\params\rig_params.json'

# start up our lil buddy and have him report when textures start moving
stimBuddy = stimulus_buddies.StimulusBuddy(
    reporting="onMotion", outputMethod="print", savePath=save_path,
    default_params_path= params, comms = None)

# create a texture
grate_gray_tex = textures.GratingGrayTex(
    texture_size=1024,
    frequency=8,
)
sin_gray_tex = textures.SinGrayTex(
    texture_size=1024,
    frequency=8,
)
# create a wholefield stimulus with that texture
grate_gray_stimulus = stimulus_details.MonocularStimulusDetails(
    texture=grate_gray_tex,
    angle=0,
    velocity=0.05,
    stationary_time=1,
    duration=3,
    hold_after=6.0,
    stim_name="moving_gray",
)
sin_gray_stimulus = stimulus_details.MonocularStimulusDetails(
    texture=sin_gray_tex,
    angle=0,
    velocity=0.05,
    stationary_time=2,
    duration=4,
    hold_after=6.0,
    stim_name="moving_gray",
)

# create a different texture
grate_red_tex = textures.GratingRgbTex(texture_size=1024, frequency=30, color=(255, 0, 0))
sin_red_tex = textures.SinRgbTex(texture_size=1024, frequency=30, color=(255, 0, 0))

# different wholefield stimulus
grate_red_stimulus = stimulus_details.MonocularStimulusDetails(
    texture=grate_red_tex,
    angle=90,
    velocity=0.05,
    stationary_time=1,
    duration=5,
    stim_name="red_sin",
)
sin_red_stimulus = stimulus_details.MonocularStimulusDetails(
    texture=sin_red_tex,
    angle=90,
    velocity=0.05,
    stationary_time=1,
    duration=8,
    stim_name="red_sin",
)
# We can create binocular by combining monocular
grate_combined_binoc_stim = stimulus_details.monocular2binocular(
    grate_gray_stimulus, grate_red_stimulus
)
sin_combined_binoc_stim = stimulus_details.monocular2binocular(
    sin_gray_stimulus, sin_red_stimulus
)

sin_red_stimulus_masked = stimulus_details.MaskedStimulusDetails(
    texture=sin_red_tex,
    angle=90,
    velocity=0.05,
    stationary_time=1,
    duration=15,
    stim_name="red_sin",
)

grate_gray_stimulus_masked = stimulus_details.MaskedStimulusDetails(
    texture=grate_gray_tex,
    angle=0,
    velocity=0.05,
    stationary_time=2,
    duration=5,
    hold_after=4.,
    stim_name="moving_gray",
)

packed_mask = stimulus_details.MaskedStimulusDetailsPack(
    stim_name = "test",
    masked_stim_details = [sin_red_stimulus_masked, grate_gray_stimulus_masked]
)

sin_red_stimulus_masked2 = stimulus_details.MaskedStimulusDetails(
    texture=sin_red_tex,
    angle=90,
    velocity=0.05,
    stationary_time=1,
    duration=15,
    stim_name="red_sin",
    masking=(0,1,0,0.5),
    transparency=0.3
)

grate_gray_stimulus_masked2 = stimulus_details.MaskedStimulusDetails(
    texture=grate_gray_tex,
    angle=0,
    velocity=0.05,
    stationary_time=2,
    duration=9,
    hold_after=4.,
    stim_name="moving_gray",
    masking=(0,0.5,0,1),
    transparency=0.5
)
grate_gray_stimulus_masked3 = stimulus_details.MaskedStimulusDetails(
    texture=grate_gray_tex,
    angle=45,
    velocity=0.05,
    stationary_time=1,
    duration=7,
    hold_after=2.,
    stim_name="moving_gray",
    masking=(0,0.75,0.2,0.6)
)


dot_stimulus_masked = stimulus_details.MaskedStimulusDetails(
    texture=textures.CircleGrayTex(),
    angle=90,
    velocity=0.1,
    duration = 10,
    stationary_time=3

)
packed_mask2 = stimulus_details.MaskedStimulusDetailsPack(
    stim_name = "test",
    masked_stim_details = [sin_red_stimulus_masked2, grate_gray_stimulus_masked2]
)
packed_mask3 = stimulus_details.MaskedStimulusDetailsPack(
    stim_name = "test",
    masked_stim_details = [sin_red_stimulus_masked2, grate_gray_stimulus_masked2, grate_gray_stimulus_masked3]
)

packed_mask4 = stimulus_details.MaskedStimulusDetailsPack(
    stim_name = "test",
    masked_stim_details = [sin_red_stimulus_masked2, grate_gray_stimulus_masked2, dot_stimulus_masked]
)

all_stimuli = [
    packed_mask,
    packed_mask2,
    packed_mask3,
    packed_mask4
]

stimBuddy.queue = all_stimuli

pstim = stimulus.ExternalStimulus(buddy=stimBuddy, params_path= params)

pstim.run()