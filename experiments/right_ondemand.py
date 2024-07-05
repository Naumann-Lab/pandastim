import sys
from pathlib import Path

from pandastim.buddies import stimulus_buddies
from pandastim.stimuli import stimulus, stimulus_details

# mySavePath = r"C:\data\pstim_stimuli\matt_output.txt"
mySavePath = r"C:\Users\matt_analysis\Downloads\matt_output.txt"

paramspath = (
    Path(sys.executable)
    .parents[0]
    .joinpath(r"Lib\site-packages\pandastim\resources\params\default_params.json")
)

stimBuddy = stimulus_buddies.StimulusBuddy(
    reporting="onMotion",
    savePath=mySavePath,
)


class localStim(stimulus.ExternalStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.baseStim = stimulus_details.MonocularStimulusDetails(angle=90)
        self.motionStim = stimulus_details.MonocularStimulusDetails(
            angle=90, duration=5, velocity=0.02, stim_name="Motion"
        )

        self.current_stimulus = self.baseStim
        self.set_stimulus()
        self.accept("m", self.trigger_motion)

    def trigger_motion(self):
        self.clear_cards(setBase=False)
        self.current_stimulus = self.motionStim
        self.set_stimulus()

    def clear_cards(self, setBase=True):
        super().clear_cards()
        if setBase:
            self.current_stimulus = self.baseStim
            self.set_stimulus()


pstim = localStim(buddy=stimBuddy, params_path=paramspath)
pstim.run()
