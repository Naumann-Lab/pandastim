"""
pandastim/utils.py

Helper functions used in multiple classes in stimulu/textures

Part of pandastim package: https://github.com/mattdloring/pandastim
"""
import os
from datetime import datetime as dt

import numpy as np
import zmq
from scipy import signal


def sin_byte(X: np.array, freq: int = 1) -> np.array:
    """
    Creates unsigned 8 bit representation of sin (T_unsigned_Byte).
    """
    sin_float = np.sin(freq * X)

    # from 0-255
    sin_transformed = (sin_float + 1) * 127.5
    return np.uint8(sin_transformed)


def grating_byte(X: np.array, freq: int = 1) -> np.array:
    """
    Unsigned 8 bit representation of a grating (square wave)
    """
    grating_float = signal.square(X * freq)

    # from 0-255
    grating_transformed = (grating_float + 1) * 127.5
    return np.uint8(grating_transformed)


def card2uv(val: float) -> float:
    """
    from model (card) -based normalized device coordinates (-1,-1 bottom left, 1,1 top right)
    appropriate for cards to texture-based uv-coordinates.

    For more on these different coordinate systems for textures:
        https://docs.panda3d.org/1.10/python/programming/texturing/simple-texturing
    """
    return 0.5 * val


def uv2card(val: float) -> float:
    """
    Transform from texture-based uv-coordinates to card-based normalized device coordinates
    """
    return 2 * val


def unpack_tex(tex) -> dict:
    vdict = vars(tex).copy()
    try:
        del vdict["texture_array"]
    except (KeyError, AttributeError):
        pass
    try:
        del vdict["texture"]
    except (KeyError, AttributeError):
        pass
    return vdict


def saving(file_path: str, append=False, *other_info) -> object:
    if "\\" in file_path:
        file_path = file_path.replace("\\", "/")

    if not append:
        val_offset = 0
        newpath = file_path
        while os.path.exists(newpath):
            val_offset += 1
            newpath = (
                file_path[: file_path.rfind("/") + 1]
                + file_path[file_path.rfind("/") + 1 :][:-4]
                + "_"
                + str(val_offset)
                + ".txt"
            )

        file_path = newpath
    print(f"Saving data to {file_path}")
    filestream = open(file_path, 'a')

    info = [str(i) for i in other_info]
    info = "_".join(info)
    if len(info) != 0:
        filestream.write(f"provided_info:{info}_{dt.now()}")
    else:
        filestream.write(f"{dt.now()}")

    filestream.flush()
    return filestream


def create_tex(input_tex_dict: dict):
    """
    this one works with the tex_ flag header
    """
    import inspect

    from pandastim.stimuli import textures

    texture_map_dict = {
        "rgb_field": textures.RgbTex,
        "gray_circle": textures.CircleGrayTex,
        "sin_gray": textures.SinGrayTex,
        "sin_rgb": textures.SinRgbTex,
        "grating_gray": textures.GratingGrayTex,
        "grating_rgb": textures.GratingRgbTex,
        "blank_tex": textures.BlankTex,
        "circs": textures.CalibrationTriangles,
        "radial_sin_centering": textures.RadialSinCube,
    }
    texFxn = texture_map_dict[input_tex_dict["tex_texture_name"]]
    # 4: to take off the 'tex_' we added earlier
    tex_dict = {
        k[4:]: v
        for k, v in input_tex_dict.items()
        if k[4:] in list(inspect.signature(texFxn).parameters)
        or k[4:] in list(inspect.signature(textures.TextureBase).parameters)
    }
    return texFxn(**tex_dict)


def createTexture(input_tex_dict: dict):
    """
    this one works generically from return_dict
    """
    import inspect

    from pandastim.stimuli import textures

    texture_map_dict = {
        "rgb_field": textures.RgbTex,
        "gray_circle": textures.CircleGrayTex,
        "sin_gray": textures.SinGrayTex,
        "sin_rgb": textures.SinRgbTex,
        "grating_gray": textures.GratingGrayTex,
        "grating_rgb": textures.GratingRgbTex,
        "blank_tex": textures.BlankTex,
        "circs": textures.CalibrationTriangles,
        "radial_sin_centering": textures.RadialSinCube,
    }
    texFxn = texture_map_dict[input_tex_dict["texture_name"]]

    tex_dict = {
        k: v
        for k, v in input_tex_dict.items()
        if k in list(inspect.signature(texFxn).parameters)
        or k in list(inspect.signature(textures.TextureBase).parameters)
    }
    return texFxn(**tex_dict)


def legacy2current(
    stim_df, tex="grating_gray", frequency=32, duration=15, stationary_time=10
):
    import inspect

    from pandastim.stimuli.stimulus_details import (BinocularStimulusDetails,
                                                    MonocularStimulusDetails)

    texDict = {"texture_name": tex, "frequency": frequency}
    createdTexture = createTexture(texDict)
    createdTextures = (createdTexture, createdTexture)
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
            stimDict["velocity"] = float(stimDict["velocity"])
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


def generate_stimSequence(
    stim_df
):
    import inspect

    from pandastim.stimuli.stimulus_details import (BinocularStimulusDetails,
                                                    MonocularStimulusDetails)

    stimSequence = []
    for row_n in range(len(stim_df)):
        row = stim_df.iloc[row_n]
        stimDict = dict(row)

        texDict = {"texture_name": stimDict["tex"], "frequency": stimDict["freq"]}
        createdTexture = createTexture(texDict)
        createdTextures = (createdTexture, createdTexture)

        if hasattr(stimDict["angle"], "__iter__"): #binocular stim
            detail_dict = {
                k: v
                for k, v in stimDict.items()
                if k in list(inspect.signature(BinocularStimulusDetails).parameters)
            }

            detail_dict["duration"] = (stimDict["duration"], stimDict["duration"])
            detail_dict["stationary_time"] = (stimDict["stationary_time"], stimDict["stationary_time"])

            stimulus = BinocularStimulusDetails(texture=createdTextures, **detail_dict)
        else: #monocular stim
            stimDict["velocity"] = float(stimDict["velocity"])
            detail_dict = {
                k: v
                for k, v in stimDict.items()
                if k in list(inspect.signature(MonocularStimulusDetails).parameters)
            }
            detail_dict["duration"] = int(stimDict["duration"])
            detail_dict["stationary_time"] = int(stimDict["stationary_time"])

            stimulus = MonocularStimulusDetails(texture=createdTexture, **detail_dict)

        stimSequence.append(stimulus)
    return stimSequence



def packageLiteStim(stimDetails):
    match type(stimDetails).__name__:
        case "MonocLite":
            stimDict = {
                "stim_name": stimDetails.stim_name,
                "angle": stimDetails.angle,
                "velocity": stimDetails.velocity,
                "stationary_time": stimDetails.stationary_time,
                "duration": stimDetails.duration,
            }
            texDict = {
                "frequency": stimDetails.frequency,
                "light_value": stimDetails.light_value,
                "dark_value": stimDetails.dark_value,
                "texture_size": stimDetails.texture_size,
                "texture_name": stimDetails.texture_name,
            }
            return stimDict, texDict
        case "BinocLite":
            stimDict = {
                "stim_name": stimDetails.stim_name,
                "angle": stimDetails.angle,
                "velocity": stimDetails.velocity,
                "stationary_time": stimDetails.stationary_time,
                "duration": stimDetails.duration,
                "strip_width": stimDetails.strip_width,
                "position": stimDetails.position,
                "strip_angle": stimDetails.strip_angle,
            }
            texDict = [
                {
                    "frequency": stimDetails.frequency[0],
                    "light_value": stimDetails.light_value[0],
                    "dark_value": stimDetails.dark_value[0],
                    "texture_size": stimDetails.texture_size,
                    "texture_name": stimDetails.texture_name[0],
                },
                {
                    "frequency": stimDetails.frequency[1],
                    "light_value": stimDetails.light_value[1],
                    "dark_value": stimDetails.dark_value[1],
                    "texture_size": stimDetails.texture_size,
                    "texture_name": stimDetails.texture_name[1],
                },
            ]

            return stimDict, texDict
        case _:
            print(f"{type(stimDetails).__name__} stimulus type not understood")


class Subscriber:
    """
    Subscriber wrapper class for zmq.
    Default topic is every topic ("").
    """

    def __init__(self, port="1234", topic="", ip=None):
        self.port = port
        self.topic = topic
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        if ip is not None:
            self.socket.connect(ip + str(self.port))
        else:
            self.socket.connect("tcp://localhost:" + str(self.port))
        self.socket.subscribe(self.topic)

    def kill(self):
        self.socket.close()
        self.context.term()


class Publisher:
    """
    Publisher wrapper class for zmq.
    """

    def __init__(self, port="1234"):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://*:" + self.port)

    def kill(self):
        self.socket.close()
        self.context.term()
