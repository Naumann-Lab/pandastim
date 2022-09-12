import json
import sys
import threading as tr
import time
from datetime import datetime as dt
from pathlib import Path

import zmq
from direct.showbase import DirectObject
from direct.showbase.MessengerGlobal import messenger

from pandastim import utils
from pandastim.stimuli import stimulus_details

try:
    from scopeslip import planeAlignment
except ImportError:
    print("alignment unavailable, no scopeslip package found")


class StimulusBuddy(DirectObject.DirectObject):
    def __init__(
        self,
        reporting="onMotion",
        receipts=True,
        outputMethod="print",
        pstim_comms=None,
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
        assert outputMethod in outputMethods, f"{reporting} not in reportingMethods"
        self.outputMethod = outputMethod
        if outputMethod == "zmq":
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

        if pstim_comms:
            self.subscriber = utils.Subscriber(**pstim_comms)
            self.run_sub = tr.Thread(target=self.input)
            self.run_sub.start()

    def pauseStatus(self, pause_status):
        if pause_status and not self._pauseStatus:
            self.queue = [self.lastReturnedStim] + self.queue
            print("tried to add to queue")
        self._pauseStatus = pause_status

    def position(self, newposition):
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
            # print(topic)

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


class AligningStimBuddy(StimulusBuddy):
    """

    this lad plays nicely with the gui, they chat back and forth

    for directed control use the other guy

    """

    def __init__(self, alignmentComms, runningVolumes=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.aligning = False

        self.requiresAlignment = False
        self.runningVolumes = runningVolumes

        self.aSub = utils.Subscriber(port=alignmentComms["wt_output"])
        self.aPub = utils.Publisher(port=alignmentComms["wt_input"])

        self.alignmentThread = tr.Thread(target=self.msg_reception)
        self.alignmentThread.start()

    def msg_reception(self):
        while self._running:
            topic = self.aSub.socket.recv_string()
            message = self.aSub.socket.recv_pyobj()

            match topic:
                case "alignment":

                    match message.split("_"):
                        case ["pause"]:
                            messenger.send("pause")
                            self.output(f"alignment: status: pause_request")
                        case ["unpause"]:
                            messenger.send("unpause")
                            self.output(f"alignment: status: unpause_request")
                        case ["movementAmount", moveAmt]:
                            self.output(
                                f"alignment: status: completed with {moveAmt} movement"
                            )
                            self.aligning = False
                        case _:
                            print(f"{message}: message not understood")

                case _:
                    print(f"{topic}: topic not understood")

    def proceed_alignment(self):
        self.output(f"alignment: status: started")
        self.aPub.socket.send_string(f"stimbuddy", zmq.SNDMORE)
        self.aPub.socket.send_pyobj(f"proceed")

    def wrap_up(self):
        self._running = False
        self.alignmentThread.join()

    def request_stimulus(self):
        if self._pauseStatus:
            if self._stimulus:
                return None
            else:
                if not self.aligning:
                    self.proceed_alignment()
                    self.aligning = True
                else:
                    pass
        elif len(self.queue) == 0:
            return None
        else:
            self.lastReturnedStim = self.pop_queue()
            return self.lastReturnedStim


class AlignmentTyrantBuddy(StimulusBuddy):
    """
    this is the alignment tyrant
    no gui -- just runs stuff on its own

    requires a supplied target image
    """

    def __init__(self, walky_talky, target_image, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from scopeslip import zmqComm

        assert isinstance(
            walky_talky, zmqComm.WalkyTalky
        ), "walky talky must be provided"

        self.wt = walky_talky
        self.target_image = target_image


class MultiSessionBuddy(AlignmentTyrantBuddy):
    """
    builds on tyrant -- this one is set up to stop and restart
    """

    def __init__(self, pauseHours=4, repeats=10, um_steps=3, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.baseQueue = None  # instantiate this to a copy of the queue the first time we do anything
        self.oneoff = 0

        self.pauseDuration = pauseHours
        self.repeats = repeats  # experiment repeats
        self.n_um = um_steps

    def request_stimulus(self):
        if self.oneoff == 0:
            self.baseQueue = self.queue.copy()
            self.oneoff += 1

        if self._pauseStatus:
            return None
        elif len(self.queue) == 0:
            if self.repeats > 0:
                self.repeats -= 1

                ## minor sleep to get trailing frames
                time.sleep(25)  # 25 seconds of trailing frames
                self.wt.pub.socket.send(b"RESET")
                time.sleep(1)
                self.wt.pub.socket.send(b"s4 shutOff")
                time.sleep(1)
                self.wt.pub.socket.send(b"RUN")
                ### self.wt.send() ### this is command for shuttering & shit
                self.timeHolder(self.pauseDuration)
                self.wt.pub.socket.send(b"s1 s3 shutOn")
                time.sleep(1.5)
                self.wt.pub.socket.send(b"RESET")
                time.sleep(1.5)
                self.wt.pub.socket.send(b"RUN")
                time.sleep(1.5)

                ### DO THE BIG ALIGNMENT DOODADS ###
                self.output(f"doing the alignment things")
                someMovementDictionary = {
                    0: -self.n_um * 2,
                    1: -self.n_um,
                    2: 0,
                    3: self.n_um,
                    4: self.n_um * 2,
                }
                self.wt.pub.socket.send(b"RESET")
                time.sleep(1)
                self.compStack = self.wt.gather_stack(spacing=self.n_um, reps=10)
                pa = planeAlignment.PlaneAlignment(
                    target=self.target_image,
                    stack=self.compStack,
                    method="otsu",
                )
                self.myMatch = pa.match_calculator()
                moveAmount = someMovementDictionary[self.myMatch]
                self.wt.move_piezo_n(moveAmount)
                self.output(f"alignment: status: completed with {moveAmount} movement")

                self.wt.pub.socket.send(b"RESET")
                time.sleep(1)
                self.wt.pub.socket.send(b"s1 s3")
                time.sleep(1)
                self.wt.pub.socket.send(b"RUN")

                ### DIRECTLY USE THE WALKYTALKY OBJECT PRESENT ###

                ### DONE DOIN THE ALIGNMENT DOODADS & STUFFS ###

                self.queue.extend(self.baseQueue)
                self.lastReturnedStim = self.pop_queue()
                return self.lastReturnedStim
            else:
                return None
        else:
            self.lastReturnedStim = self.pop_queue()
            return self.lastReturnedStim

    @staticmethod
    def timeHolder(hours):
        """
        this lad is a really agressive implementation of a time pause

        :param hours: hours to pause for
        :return:
        """
        seconds = hours * 60 * 60
        time.sleep(seconds)


class GUIBuddy(StimulusBuddy):
    def __init__(self, inputPort, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gSub = utils.Subscriber(port=inputPort)

        self.guiThread = tr.Thread(target=self.msg_reception)
        self.guiThread.start()

    def msg_reception(self):
        while self._running:
            topic = self.gSub.socket.recv_string()
            message = self.gSub.socket.recv_pyobj()

            someTex = utils.createTexture(message["texture"])
            someStim = stimulus_details.MonocularStimulusDetails(texture=someTex)
            messenger.send("directDriven", [someStim])
