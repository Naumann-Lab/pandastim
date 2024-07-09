"""
pandastim/stimuli/stimulus_details.py

defines strict parameters for stimuli to follow according to defined type -- fake static typed

Part of pandastim package: https://github.com/mattdloring/pandastim
"""
from dataclasses import dataclass

import numpy as np

from pandastim import utils


@dataclass(frozen=True)
class StimulusDetails:
    """Contains details about a given stimulus"""

    stim_name: str


@dataclass(frozen=True)
class MonocLite(StimulusDetails):
    stim_name: str = f"unnamed_monocular_stimulus"

    angle: int = 0
    velocity: float = 0.0
    frequency: int = 60
    stationary_time: int = 0
    duration: int = -1  # defaults to going forever
    hold_after: float = np.nan
    light_value: int = 255
    dark_value: int = 0
    texture_size: tuple = (1024, 1024)
    texture_name: str = "grating_gray"

    # default master for monocular stimuli -- can be passed in local usages
    master = {
        "stim_name": str,
        "angle": int,
        "velocity": float,
        "frequency": int,
        "stationary_time": float,
        "hold_after": float,
        "duration": float,
        "light_value": int,
        "dark_value": int,
        "texture_size": (int, int),
        "texture_name": str,
    }

    def __post_init__(self):
        """Because python isn't static lets force things here"""
        if self.master:
            for k, v in self.master.items():
                assert k in self.__dict__.keys(), f"must provide {k}"
                if not isinstance(v, tuple) and not isinstance(v, list):
                    assert isinstance(getattr(self, k), v), f"{k} must be type: {v}"
                else:
                    assert isinstance(
                        getattr(self, k)[0], v[0]
                    ), f"{k}0 must be type: {v}"
                    assert isinstance(
                        getattr(self, k)[1], v[1]
                    ), f"{k}1 must be type: {v}"

    def return_dict(self):
        stim_dict, tex_dict = utils.packageLiteStim(self)
        return {"stimulus": stim_dict, "texture": tex_dict}


@dataclass(frozen=True)
class BinocLite(StimulusDetails):
    stim_name: str = f"unnamed_binocular_stimulus"

    angle: tuple = (0, 0)
    velocity: tuple = (0.0, 0.0)
    stationary_time: tuple = (0.0, 0.0)
    duration: tuple = (-1.0, -1.0)  # defaults to going forever
    hold_after: tuple = (np.nan, np.nan)
    strip_width: int = 8
    position: tuple = (0.0, 0.0)
    strip_angle: int = 0
    light_value: tuple = (255, 255)  # l, r tex
    dark_value: tuple = (0, 0)
    frequency: tuple = (48, 48)
    texture_size: tuple = (1024, 1024)
    texture_name: tuple = ("grating_gray", "grating_gray")

    master = {
        "stim_name": str,
        "angle": (int, int),
        "velocity": (float, float),
        "stationary_time": (float, float),
        "duration": (float, float),
        "hold_after": (float, float),
        "strip_width": int,
        "position": (float, float),
        "strip_angle": int,
        "light_value": (int, int),
        "dark_value": (int, int),
        "frequency": (int, int),
        "texture_size": (int, int),
        "texture_name": (str, str),
    }

    def __post_init__(self):
        """Because python isn't static lets force things here"""
        if self.master:
            for k, v in self.master.items():
                assert k in self.__dict__.keys(), f"must provide {k}"
                if not isinstance(v, tuple) and not isinstance(v, list):
                    assert isinstance(getattr(self, k), v), f"{k} must be type: {v}"
                else:
                    assert isinstance(
                        getattr(self, k)[0], v[0]
                    ), f"{k}0 must be type: {v}"
                    assert isinstance(
                        getattr(self, k)[1], v[1]
                    ), f"{k}1 must be type: {v}"

    def return_dict(self):
        stim_dict, tex_dict = utils.packageLiteStim(self)
        return {"stimulus": stim_dict, "texture": tex_dict}


@dataclass(frozen=True)
class MonocularStimulusDetails(StimulusDetails):
    """
    Contains details about a given whole-field stimulus
    General implementation assumes duration is full time, stationary time is therefore a subset of that time
    ex: 2 s statonary and 10 s duration runs a total of 10 seconds
    """

    from pandastim.stimuli import textures

    # required
    angle: int = 0
    velocity: float = 0.0

    # defaults
    stationary_time: int = 0
    duration: int = -1  # defaults to going forever
    hold_after: float = np.nan

    # default texture is a grating, because why not
    texture: textures.TextureBase = textures.GratingGrayTex()
    stim_name: str = f"wholefield-stimulus_{velocity}_{angle}"

    # default master for monocular stimuli -- can be passed in local usages
    master = {
        "stim_name": str,
        "angle": int,
        "velocity": float,
        "stationary_time": int,
        "duration": int,
        "hold_after": float,
        "texture": textures.TextureBase,
    }

    def __post_init__(self):
        """Because python isn't static lets force things here"""
        if self.master:
            for k, v in self.master.items():
                assert k in self.__dict__.keys(), f"must provide {k}"
                assert isinstance(getattr(self, k), v), f"{k} must be type: {v}"

    def return_dict(self):
        tex_dict = utils.unpack_tex(self.texture)
        stim_dict = vars(self).copy()
        stim_dict.pop("texture")
        return {"stimulus": stim_dict, "texture": tex_dict}


@dataclass(frozen=True)
class BinocularStimulusDetails(StimulusDetails):
    """
    Contains details about a given stimulus where each side is controlled independently
    This default implementation assumes the two textures are equal in size -- will likley run with nonequal sizes
    but may look wonk
    """

    from pandastim.stimuli import textures

    # required
    angle: tuple = (0, 0)
    velocity: tuple = (0.0, 0.0)

    # defaults
    stationary_time: tuple = (0, 0)
    duration: tuple = (-1, -1)  # defaults to going forever
    hold_after: tuple = (np.nan, np.nan)
    strip_width: int = 8
    position: tuple = (0, 0)
    strip_angle: int = 0

    texture: tuple = (
        textures.GratingGrayTex(),
        textures.GratingGrayTex(),
    )
    stim_name: str = f"binocular-stimulus_{velocity}_{angle}"

    master = {
        "stim_name": str,
        "angle": tuple,
        "velocity": tuple,
        "stationary_time": tuple,
        "hold_after": tuple,
        "duration": tuple,
        "strip_width": int,
        "position": tuple,
        "strip_angle": int,
        "texture": tuple,
    }

    def __post_init__(self):
        """Because python isn't static lets force things here"""
        if self.master:
            for k, v in self.master.items():
                assert k in self.__dict__.keys(), f"must provide {k}"
                assert isinstance(getattr(self, k), v), f"{k} must be type: {v}"

    def return_dict(self):
        tex0_dict = utils.unpack_tex(self.texture[0])
        tex1_dict = utils.unpack_tex(self.texture[1])

        stim_dict = vars(self).copy()
        stim_dict.pop("texture")
        return {"stimulus": stim_dict, "texture": [tex0_dict, tex1_dict]}


def monocular2binocular(
    monoc1: MonocularStimulusDetails,
    monoc2: MonocularStimulusDetails,
    strip_width: int = 12,
    strip_angle: int = 0,
    name: str = "default",
) -> BinocularStimulusDetails:

    stim1_dict = vars(monoc1)
    stim2_dict = vars(monoc2)
    keys = stim1_dict.keys()

    if name == "default":
        new_name = stim1_dict["stim_name"] + "_&_" + stim2_dict["stim_name"]
    else:
        new_name = name

    new_stim_dict = {
        "stim_name": new_name,
        "strip_width": strip_width,
        "strip_angle": strip_angle,
    }

    specialCases = ["stim_name", "texture_size"]

    for key in keys:
        if key not in specialCases:
            new_stim_dict[key] = (stim1_dict[key], stim2_dict[key])
    return BinocularStimulusDetails(**new_stim_dict)


def legacy2current(stim_df, tex="grating_gray", duration=15, stationary_time=10):#trasnferred to utils...
    import inspect

    texDict = {"texture_name": "grating_gray", "frequency": 48}
    createdTexture = utils.createTexture(texDict)
    createdTextures = (createdTexture, createdTexture)  # assumes same textures
    stimSequence = []
    for row_n in range(len(stim_df)):
        row = stim_df.iloc[row_n]
        stimDict = dict(row)
        if hasattr(stimDict["angle"], "__iter__"):
            detail_dict = {
                k: v
                for k, v in stimDict.items()
                if k in list(inspect.signature(BinocularStimulusDetails).parameters)
            }

            detail_dict["duration"] = (duration, duration)
            detail_dict["stationary_time"] = (stationary_time, stationary_time)
            stimulus = BinocularStimulusDetails(texture=createdTextures, **detail_dict)
        else:
            detail_dict = {
                k: v
                for k, v in stimDict.items()
                if k in list(inspect.signature(MonocularStimulusDetails).parameters)
            }
            detail_dict["duration"] = duration
            detail_dict["stationary_time"] = stationary_time
            stimulus = MonocularStimulusDetails(texture=createdTexture, **detail_dict)

        stimSequence.append(stimulus)
    return stimSequence

def legacy2current_singlestim(
    stim_df, tex="grating_gray", frequency=32, duration=15, stationary_time=10, texture_size = 1024,
    dark_value = 0, light_value = 255):
    """for a single stimuli. legacy: dataframe format; current: stimulus_details format"""
    import inspect

    from pandastim.stimuli.stimulus_details import (BinocularStimulusDetails,
                                                    MonocularStimulusDetails)

    texDict = {"texture_name": tex, "frequency": frequency, "texture_size": texture_size,
               "light_value": light_value, "dark_value": dark_value}
    createdTexture = utils.createTexture(texDict)
    createdTextures = (createdTexture, createdTexture)

    stimDict = dict(stim_df)
    if hasattr(stimDict["angle"], "__iter__"):
        detail_dict = {
                k: v
                for k, v in stimDict.items()
                if k in list(inspect.signature(BinocularStimulusDetails).parameters)
            }

        detail_dict["duration"] = (duration, duration)
        detail_dict["stationary_time"] = (stationary_time, stationary_time)
        stimulus = BinocularStimulusDetails(texture=createdTextures, **detail_dict)
    else:
        stimDict["velocity"] = float(stimDict["velocity"])
        detail_dict = {
                k: v
                for k, v in stimDict.items()
                if k in list(inspect.signature(MonocularStimulusDetails).parameters)
            }
        detail_dict["duration"] = duration
        detail_dict["stationary_time"] = stationary_time
        stimulus = MonocularStimulusDetails(texture=createdTexture, **detail_dict)

    return stimulus