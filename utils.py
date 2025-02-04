"""
pandastim/utils.py

Helper functions used in multiple classes in stimulu/textures

Part of pandastim package: https://github.com/mattdloring/pandastim
"""
import numpy as np
import threading
import zmq
import time
import os
import json
import sys
import pandas as pd

from direct.showbase import DirectObject
from direct.showbase.MessengerGlobal import messenger


from scipy import signal
from datetime import datetime as dt
from pathlib import Path

def port_provider():
    """
    returns a random free port on PC
    """
    c = zmq.Context()
    s = c.socket(zmq.SUB)
    rand_port = s.bind_to_random_port('tcp://*', min_port=5000, max_port=8000, max_tries=100)
    c.destroy()
    return rand_port

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
                + "_pstim.txt"
            )

        file_path = newpath
    print(f"Saving data to {file_path}")
    filestream = open(file_path, "a")

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
    print(tex_dict)
    return texFxn(**tex_dict)


def legacy2current(
    stim_df, tex="grating_gray", frequency=32, duration=15, stationary_time=10
):
    """legacy: dataframe format; current: dictionrary format"""
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


class Monitor(DirectObject.DirectObject):
    """
    Use a subscriber to continuously monitor publisher, and
    emit messages for the panda3d event handler.

    This is used for closed-loop stimuli.

    Matt: this is a working hack : see working/monitor_notes.txt.
    """

    def __init__(self, subscriber):
        self.sub = subscriber
        self.run_thread = threading.Thread(target=self.run)
        self.run_thread.daemon = True  # let's you kill it
        self.run_thread.start()

    def run(self):
        while True:
            data = self.sub.socket.recv()  # recv_string()
            topic, message = data.split()
            # emit message for panda3d (convert from byte to string)
            messenger.send("stim" + str(message, 'utf-8'))

    def kill(self):
        self.run_thread.join()


class MonitorDataPass(DirectObject.DirectObject):
    """
    this monitor passes the data through to pandas
    """

    def __init__(self, subscriber, subscriber2=None):

        self.sub = subscriber
        self.run_thread = threading.Thread(target=self.run)
        self.run_thread.daemon = True
        self.run_thread.start()

        if subscriber2 is not None:
            self.sub2 = subscriber2
            self.run_thread2 = threading.Thread(target=self.run2)
            self.run_thread2.daemon = True
            self.run_thread2.start()

    def run(self):
        # this is run on a separate thread so it can sit in a loop waiting to receive messages
        while True:
            try:
                topic = self.sub.socket.recv_string()
                data = self.sub.socket.recv_pyobj()
                # print(data)
                # this is a duplication at the moment, but provides an intermediate processing stage, may be useful later
                if 'load' in data:
                    messenger.send('stimulus_loader', [data])
                elif 'live' in data:
                    messenger.send('stimulus_update', [data])
                else:
                    messenger.send('stimulus', [data])
            except Exception as e:
                print(e)

    def run2(self):
        # this is run on a separate thread so it can sit in a loop waiting to receive messages
        while True:
            try:
                topic = self.sub2.socket.recv_string()
                print(topic)
                data = self.sub2.socket.recv_pyobj()
                print(data)
                # print(data)
                # this is a duplication at the moment, but provides an intermediate processing stage, may be useful later
                messenger.send('stimulus', [data])
            except:
                pass

    def kill(self):
        self.run_thread.join()


class Emitter(DirectObject.DirectObject):
    """
    Given three lists (x, y, theta):
    emit the xytheta values in the list with period seconds betwween them, pause, and repeat.
    """

    def __init__(self, x_vals, y_vals, theta_vals, period=0.2, pause=1.0):
        self.x_vals = x_vals
        self.y_vals = y_vals
        self.theta_vals = theta_vals
        self.num_points = len(self.x_vals)
        assert (len(x_vals) == len(y_vals) == len(theta_vals)), "x y and theta must be same length"
        self.period = period
        self.pause = pause
        self.killed = False
        self.run_thread = threading.Thread(target=self.run)
        self.run_thread.daemon = True
        self.run_thread.start()

    def run(self):
        while True:
            for ind, (x_val, y_val, theta_val) in enumerate(zip(self.x_vals, self.y_vals, self.theta_vals)):
                # print(f"stim {x_val} {y_val} {theta_val}")
                messenger.send("stim", [x_val, y_val, theta_val])
                if ind == 0:
                    time.sleep(self.pause)
                else:
                    time.sleep(self.period)
            print(f"Emitter cycle done: pausing {self.pause} seconds.")
            time.sleep(self.pause)

    def kill(self):
        self.run_thread.join()


def sequence_runner(df, port="5005", listening_port='5006'):
    # this runs a dataframe of stimuli for you
    # time.sleep(1)
    _context = zmq.Context()
    _socket = _context.socket(zmq.PUB)
    _socket.bind('tcp://*:' + str(port))
    stimulus_topic = 'stim'

    if 'stationary_time' not in df.columns:
        df.loc[:, 'stationary_time'] = 0

    stim_n = 0

    listening_context = zmq.Context()
    listening_socket = listening_context.socket(zmq.SUB)
    listening_socket.connect(str("tcp://localhost:") + str(listening_port))

    print('waiting on ', listening_port)
    # this hangs until pandastim sets out its running message
    data = listening_socket.recv_pyobj()
    print('running')
    current_length = df.loc[stim_n].duration + df.loc[stim_n].stationary_time
    t0 = time.time()

    _socket.send_string(stimulus_topic, zmq.SNDMORE)
    _socket.send_pyobj(df.loc[stim_n])
    print('sent first')

    while stim_n <= len(df) - 1:
        if time.time() - t0 <= current_length:
            pass
        else:
            stim_n += 1

            current_length = df.loc[stim_n].duration + df.loc[stim_n].stationary_time
            t0 = time.time()
            _socket.send_string(stimulus_topic, zmq.SNDMORE)
            _socket.send_pyobj(df.loc[stim_n])


def img_receiver(socket, ):
    msg_dict = socket.recv_json()
    msg = socket.recv()
    _img = np.frombuffer(bytes(memoryview(msg)), dtype=msg_dict['dtype'])
    img = _img.reshape(msg_dict['shape'])
    return np.array(img)


def reduce_to_pi(ar):
    """Reduce angles to the -pi to pi range"""
    return np.mod(ar + np.pi, np.pi * 2) - np.pi


def angle_mean(angles, axis=0):
    """Correct calculation of a mean of an array of angles
    """
    return np.arctan2(np.nansum(np.sin(angles), axis), np.nansum(np.cos(angles), axis))


def angle_diff(a1, a2):
    '''
    correct calculaion of difference of two angles (radians)
    '''
    from math import tau
    return min(a2 - a1, a2 - a1 + tau, a2 - a1 - tau, key=abs)


def get_calibration_params():
    param_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params\caliparams.json')
    if os.path.exists(param_path):
        with open(param_path) as json_file:
            data = json.load(json_file)
        return data
    else:
        return None


def load_params(param_path):
    with open(param_path) as json_file:
        data = json.load(json_file)
    return data


def create_radial_sin(texture_size):
    from pandastim.stimuli import textures, stimulus_details
    stack = []
    num_slices = 190
    phase_change = 0.1
    phase = 0
    for slice_num in range(num_slices):
        rad_slice_texture = textures.RadialSinCube(texture_size=texture_size, phase=phase)
        rad_slice = stimulus_details.MonocularStimulusDetails(stim_name = 'centering rad', texture = rad_slice_texture)
        stack.append(rad_slice)
        phase += phase_change
    return stack

def dot_generator(dot_name, dot_side, dot_size_deg, x_offset_px, y_offset_px, velocity_deg, canvas_size, stationary_time, duration):
    if dot_side == 'left':
        dot_angle = 90
    elif dot_site == 'right':
        dot_angle = -90
    dot_radius_px = np.tan(np.deg2rad(dot_size_deg)) * y_offset_px * 0.5 #for radius not diameter
    dot_velocity_perc_canvas = np.tan(np.deg2rad(velocity_deg)) * y_offset_px / canvas_size
    dot = {'stim_name': [dot_name], 'angle': [dot_angle], 'velocity': [dot_velocity_perc_canvas],
                   'stim_type': ['s'], 'stationary_time': [stationary_time], 'duration': [duration],
                   'texture': ['gray_circle'], 'circle_center': [[x_offset_px, y_offset_px]],
                   'circle_radius': [dot_radius_px]}
    dot = pd.DataFrame.from_dict(dot)
    return dot

# %%
if __name__ == '__main__':
    to_test = 1
    if to_test == 0:
        # Monitor test: first turn on pub_class_toggle.py or pub_class_toggle3.py
        sub = Subscriber(topic="stim")
        m = Monitor(sub)
        time.sleep(60)
        m.kill()
    elif to_test == 1:
        # Emitter test
        x = [.1, .2, .3, .4, .5]
        y = [.2, .2, .3, .4, .5]
        theta = [10, 15, 20, 25, 30]
        em = Emitter(x, y, theta, period=1, pause=2)
        time.sleep(4)
        em.kill()


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
