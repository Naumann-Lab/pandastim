import json
import sys
import threading as tr
import time
from datetime import datetime as dt
from pathlib import Path
import pandas as pd

import zmq
from direct.showbase import DirectObject
from direct.showbase.MessengerGlobal import messenger

from pandastim import utils
from pandastim.stimuli import stimulus_details, textures

#it's behavior rig, of course no alignment
# try:
#     from scopeslip import planeAlignment
# except ImportError:
#     pass


class StimulusBuddy(DirectObject.DirectObject):
    """
    Methods:
        pauseStatus
    """
    def __init__(
        self,
        reporting="onMotion",
        comms = None,
        receipts=True,
        outputMethod="print",
        savePath=None,
        default_params_path=None,
    ):
        if not default_params_path:
            default_params_path = (
                Path(sys.executable)
                .parents[0]
                .joinpath(
                    r"Lib\site-packages\pandastim\resources\params\default_params.json"
                )
            )
        with open(default_params_path) as json_file:
            self.default_params = json.load(json_file)

        reportingMethods = [None, "onStim", "onMotion", "full"]
        assert reporting in reportingMethods, f"{reporting} not in reportingMethods"
        self.reportingMethod = reporting

        outputMethods = ["print", "zmq"]
        assert outputMethod in outputMethods, f"{outputMethod} not in outputMethods"
        self.outputMethod = outputMethod
        if outputMethod == "zmq":
            self.publisher = utils.Publisher(port = comms['buddy_stimulus_socket'])
            self.publisher = utils.Publisher(
                port=str(self.default_params["publish_port"])
            )

        if savePath:
            self.filestream = utils.saving(savePath)
        else:
            self.filestream = None

        match self.reportingMethod:
            case "onStim":
                self._lastmessage = None
            case "onMotion":
                self._lastmessage = [None, None]
            case _:
                self._lastmessage = None

        ## underscores for tracking here, not under'd for showbase vars
        self._position = 0
        self._motion = False
        self._stimChange = False
        self._stimulus = None
        self._running = True
        self._pauseStatus = False
        self.lastReturnedStim = None

        self.receipts = receipts
        self.queue = []

        #if pstim_comms:
        #    self.subscriber = utils.Subscriber(**pstim_comms)
        #    self.run_sub = tr.Thread(target=self.input)
        #    self.run_sub.start()

    def pauseStatus(self, pause_status):
        """
        Sets attribute defining pause status _pauseStatus
        Args:
            pause_status: bool
                buddy -> protocol publisher socket message.  TRUE if paused.
            
        """
        if pause_status and not self._pauseStatus:
            self.queue = [self.lastReturnedStim] + self.queue
            print("tried to add to queue")
        self._pauseStatus = pause_status

    def position(self, newposition):
        """
        Resets current _position attribute to value provided by newposition

        """
        if newposition != 0 and newposition != self._position:
            self._position = newposition
            self._motion = True
            # print(newposition)
        else:
            self._motion = False

    def stimulus(self, newstimulus):
        try:
            if (
                    newstimulus.stim_name != self._stimulus.stim_name
                and self._stimChange == False
            ):
                self._stimulus = newstimulus
                self._stimChange = True
            else:
                self._stimChange = False
        except AttributeError:
            # we end up here on first pass
            self._stimulus = newstimulus
            if newstimulus is not None:#before the first stimulus got assigned
                self._stimChange = True

    def broadcaster(self):
        match self.reportingMethod:
            case "onStim":
                msg = self._stimulus.stim_name
                if self._lastmessage != msg and self._stimChange:
                    if self._stimulus is not None:
                        self.output(f"onStim: {self._stimulus.return_dict()}")
                    else:
                        self.output(f"onStim: {self._stimulus}")
                    self._lastmessage = msg
                    # self.output(msg)
            case "onMotion":
                msg = [self._motion, self._stimChange]
                if self._lastmessage[0] != msg[0] and not self._stimChange:
                    if self._stimulus is not None:
                        self.output(f"motionOn: {self._stimulus.return_dict()}")
                    else:
                        self.output(f"motionOn: {self._stimulus}")
                    self._lastmessage = msg
                if self._lastmessage[1] != msg[1]:
                    if self._stimulus is not None:
                        self.output(f"stimChange: {self._stimulus.return_dict()}")
                    else:
                        self.output(f"stimChange: {self._stimulus}")
                    self._lastmessage = msg
            case "full":
                self.output(
                    f"stim_{self._stimulus},motion_{self._motion},position_{self._position}"
                )
            case _:
                pass

    def input(self):
        print(f"StimulusBuddy listening on {self.subscriber.port}")
        while self._running:
            topic = self.subscriber.socket.recv_string()
            data = self.subscriber.socket.recv_pyobj()
            match topic:
                case "stim":
                    try:
                        if not isinstance(data["texture"], dict):
                            input_texture_0 = utils.createTexture(data["texture"][0])
                            input_texture_1 = utils.createTexture(data["texture"][1])

                        else:
                            input_texture = utils.createTexture(data["texture"])

                    except Exception as e:
                        print(e)
                        print(f"failed to create texture {data}")

                    try:
                        if not isinstance(data["texture"], dict):
                            input_stimulus = stimulus_details.BinocularStimulusDetails(
                                texture=(input_texture_0, input_texture_1),
                                **data["stimulus"],
                            )
                        else:
                            input_stimulus = stimulus_details.MonocularStimulusDetails(
                                texture=input_texture, **data["stimulus"]
                            )

                        self.queue.append(input_stimulus)
                        if self.receipts:
                            self.output(
                                f"pstimReceipts: queueAddition: {input_stimulus.return_dict()}"
                            )
                        # print(f'added stimulus to queue: {input_stimulus}')
                    except Exception as e:
                        print(e)
                        print(f"failed to initialize stimulus {data}")
                        if self.receipts:
                            self.output(f"pstimReceipts: ERROR: {e}")

                case _:
                    print(f"message {topic} not understood")

    def output(self, msg):
        match self.outputMethod:
            case "print":
                print(f"pandastim {str(dt.now())} {msg}")
            case "zmq":
                self.publisher.socket.send_pyobj(f"pandastim {str(dt.now())} {msg}")
                print(f"pandastim {str(dt.now())} {msg}")
            case _:
                pass

        self.save(str(dt.now()) + "_&_" + msg)

    def save(self, msg):
        if self.filestream:
            try:
                stiminfo = self._stimulus.return_dict()
            except:
                stiminfo = None
            timestamp = str(dt.now())

            self.filestream.write("\n")
            self.filestream.write(f"{timestamp}_&_{msg.split('_&_')[1]}")
            # self.filestream.write("\n")
            # self.filestream.write(f"{timestamp}_&_{stiminfo}")
            self.filestream.flush()

    def view_queue(self):
        return self.queue

    def append_queue(self, item):
        self.queue.append(item)

    def pop_queue(self, index=0):
        item = self.queue.pop(index)
        return item

    def request_stimulus(self):
        if self._pauseStatus:
            return None
        elif len(self.queue) == 0:
            return None
        else:
            self.lastReturnedStim = self.pop_queue()
            return self.lastReturnedStim

    def proceed_alignment(self):
        self.output(f"pause")


class StytraBuddy(StimulusBuddy):
    def __init__(self, comms, params_path, protocol, *args, **kwargs):
        super().__init__(comms = comms, default_params_path= params_path, *args, **kwargs)

        self.protocol_buddy_sub = utils.Subscriber(port=comms['protocol_buddy_socket'])#talking to protocol
        self.buddy_stimulus_pub = utils.Publisher(port = comms['buddy_stimulus_socket'])#talking to stimulus
        self.stytraThreadList = [tr.Thread(target=protocol, args=(comms, self.default_params)),
                                 tr.Thread(target=self.msg_reception)]
        self.centering = False #use to track centering stimulus initiation request from protocol
        self.cali_pos = (None, None)
        self.updating = False #use to track stimulus update command from protocol
        self.updating_info = None
        for thread in self.stytraThreadList:
            thread.start()

    def set_centering(self, cali_pos):
        """change centering to True so the stimulus will start centering"""
        self.centering = not self.centering
        if cali_pos != (None, None):#once cali pos is set, keeping it from being washed away
            self.cali_pos = cali_pos

    def request_centering(self):
        """Let stimulus to request the current centering status"""
        return self.centering, self.cali_pos

    def set_updating(self, updating_info):
        """change updating status to True so the stimulus will start updating, and also pass the updating info"""
        self.updating = True
        self.updating_info = updating_info

    def request_updating(self):
        """Let the stimulus to request the current updating status"""
        return self.updating, self.updating_info

    def msg_reception(self):
        self.centering = False
        self.updating = False  # assuming not updating
        while self._running:
            topic = self.protocol_buddy_sub.socket.recv_string()
            data = self.protocol_buddy_sub.socket.recv_pyobj()
            match topic:
                case "calibration_stimulus":#when receiving calibration stimulus
                    if data:#if data is True, make calibration signal the first stimulus
                        cali_params = utils.get_calibration_params()
                        if cali_params is None:
                            texture = textures.CalibrationTriangles()
                        else:
                            texture = textures.CalibrationTriangles(
                                texture_size=self.default_params['window_size'],
                                tri_size=cali_params['tri_size'],circle_radius=cali_params['circle_radius'],
                                x_offset=cali_params['x_off'], y_offset=cali_params['y_off'])
                        input_stimulus = stimulus_details.MonocularStimulusDetails(stim_name = 'calibration',
                            texture=texture, velocity=0., angle=0)
                        self.append_queue(input_stimulus)
                    elif not data:#if data is False (clicked the botton again), turn off the calibration signal and add in blank
                        blank_stimulus = stimulus_details.MonocularStimulusDetails(stim_name = 'pet turtle',
                                                                                   texture = textures.BlankTex(),
                                                                                   velocity=0., angle=0)
                        self.append_queue(blank_stimulus)#called it pet turtle because turtles are like rocks
                case "centering":
                    self.set_centering(data) #start centering
                case "stimulus":
                    data = stimulus_details.legacy2current_singlestim(data,
                                                           light_value = self.default_params['light_value'],
                                                           dark_value=self.default_params['dark_value'],
                                                           frequency = self.default_params['frequency'],
                                                           texture_size=self.default_params['window_size'])
                    self.append_queue(data)
                case "clickstim":
                    center_stimulus = stimulus_details.MonocularStimulusDetails(
                        stim_name='centerclick',
                        texture=textures.CircleGrayTex(circle_radius=50,texture_size=self.default_params['window_size']))
                    self.append_queue(center_stimulus)
                case "stimulus_update":
                    self.set_updating(data)
                case _:
                    print(
                        f"{topic} --  not understood, failed"
                    )


class BrukerBuddy(StimulusBuddy):
    def __init__(self, comms, params_path, protocol, *args, **kwargs):
        super().__init__(comms = comms, default_params_path= params_path, *args, **kwargs)

        self.protocol_buddy_sub = utils.Subscriber(port=comms['protocol_buddy_socket'])#talking to protocol
        self.buddy_protocol_pub = utils.Publisher(port=comms['buddy_protocol_socket'])#talking to protocol
        self.buddy_stimulus_pub = utils.Publisher(port = comms['buddy_stimulus_socket'])#talking to stimulus
        self.alignment_buddy_sub = utils.Subscriber(port='7979')
        #self.buddy_alignment_pub = utils.Subscriber(port='5021')

        #self.alignment_sub = utils.Subscriber(prot = comms['protocol_buddy_socket'])
        self.stytraThreadList = [tr.Thread(target=protocol, args=(comms, self.default_params)),
                                 tr.Thread(target=self.msg_reception),
                                 tr.Thread(target=self.alignment_reception)]
        self.updating = False #use to track stimulus update command from protocol
        self.updating_info = None
        for thread in self.stytraThreadList:
            thread.start()

    def set_updating(self, updating_info):
        """change updating status to True so the stimulus will start updating, and also pass the updating info"""
        self.updating = True
        self.updating_info = updating_info

    def request_updating(self):
        """Let the stimulus to request the current updating status"""
        return self.updating, self.updating_info

    def alignment_reception(self):
        """This function keeps runing in the background to receive messages from the alignment"""
        while self._running:
            try:#also talk to alignment
                alignment = self.alignment_buddy_sub.socket.recv_string(flags=zmq.NOBLOCK)
                self.alignmentpause = self.alignment_buddy_sub.socket.recv_pyobj(flags=zmq.NOBLOCK)# if pause, it will give an object
                self.buddy_protocol_pub.socket.send_string('pause_status')
                self.buddy_protocol_pub.socket.send_pyobj(self.alignmentpause)#'unpause'
                print('alignment done, next imaging starts, unpause stimulus')
            except zmq.Again:
                # Nothing received this time, following previous status
                pass

    def msg_reception(self):
        self.centering = False
        self.updating = False  # assuming not updating
        
        while self._running:
            topic = self.protocol_buddy_sub.socket.recv_string()
            data = self.protocol_buddy_sub.socket.recv_pyobj()
            match topic:
                case "calibration_stimulus":#when receiving calibration stimulus
                    if data:#if data is True, make calibration signal the first stimulus
                        cali_params = utils.get_calibration_params()
                        if cali_params is None:
                            texture = textures.CalibrationTriangles()
                        else:
                            texture = textures.CalibrationTriangles(
                                texture_size=self.default_params['window_size'],
                                tri_size=cali_params['tri_size'],circle_radius=cali_params['circle_radius'],
                                x_offset=cali_params['x_off'], y_offset=cali_params['y_off'])
                        input_stimulus = stimulus_details.MonocularStimulusDetails(stim_name = 'calibration',
                            texture=texture, velocity=0., angle=0, angular_velocity = 0.)
                        self.append_queue(input_stimulus)
                    elif not data:#if data is False (clicked the botton again), turn off the calibration signal and add in blank
                        blank_stimulus = stimulus_details.MonocularStimulusDetails(stim_name = 'pet turtle',
                                                                                   texture = textures.BlankTex(),
                                                                                   velocity=0., angle=0,
                                                                                   angular_velocity = 0.)
                        self.append_queue(blank_stimulus)#called it pet turtle because turtles are like rocks
                case "stimulus":
                    if data.stim_name == 'pause':
                        self.buddy_protocol_pub.socket.send_string('pause_status')
                        self.buddy_protocol_pub.socket.send_pyobj('pause')
                    else:
                        data = stimulus_details.legacy2current_singlestim(data,
                                                        light_value = self.default_params['light_value'],
                                                        dark_value=self.default_params['dark_value'],
                                                        frequency = self.default_params['frequency'],
                                                        texture_size=self.default_params['window_size'])

                        self.append_queue(data)
                case "stimulus_update":
                    self.set_updating(data)
                case _:
                    print(  f"{topic} --  not understood, failed")