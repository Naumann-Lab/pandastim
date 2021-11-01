from direct.showbase import DirectObject
from direct.showbase.MessengerGlobal import messenger

from pandastim import utils, textures
from pandastim.behavior import calibration

from scipy.signal.signaltools import wiener
from math import radians, degrees

import sys
import zmq
import cv2
import time

import threading as tr
import numpy as np
import pygetwindow as gw


class BaseProtocol(DirectObject.DirectObject):
    def __init__(self, stimuli, ports, defaults, rig):

        self.stimuli = stimuli
        self.defaults = defaults
        self.rig_number = rig

        self.centered_pt = self.defaults['center_coord']

        # set up handshake communication with stytra for experiment triggering
        self.experiment_trigger_context = zmq.Context()
        self.experiment_trigger_comm = self.experiment_trigger_context.socket(zmq.REP)
        self.experiment_trigger_comm.bind('tcp://*:' + ports['go_socket'])

        # this receives positional information from sytra
        self.position_comm = utils.Subscriber(port=ports['tracking_socket'])

        # this port is used for centering, calibrating, and toggling calibration stimulus
        self.stytra_cam_output_port = utils.Subscriber(ports['image_socket'])
        self.cam_outputs_thread = tr.Thread(target=self.centering_calibration)

        # this is used to publish timing information to update the stytra loading bar
        # timing takes in [max time, elapsed time]
        self.timing_comm = utils.Publisher(port=ports['timing_socket'])

        self.experiment_running = False
        self.experiment_finished = False

        self.fish_data = [[np.nan, np.nan, np.nan]]
        self.last_fish_present = 0
        self.max_buffer = 500

        self.cam_outputs_thread.start()

        try:
            self.proj2cam, self.cam2proj = calibration.load_params(self.rig_number)
        except FileNotFoundError:
            print("no calibration files found please calibrate")

        self.run_experiment()

    def run_experiment(self):
        # this should hang here until we handshake
        msg = self.experiment_trigger_comm.recv_string()
        self.experiment_trigger_comm.send_string('stim', zmq.SNDMORE)
        self.experiment_trigger_comm.send_pyobj(['GO'])
        print('experiment began')

        self.init_time = time.time()

        try:
            self.proj2cam, self.cam2proj = calibration.load_params(self.rig_number)
        except FileNotFoundError:
            print("CALIBRATION FILE NOT FOUND, EXITING")
            import sys
            sys.exit()

        self.experiment_running = True

        data_stream = tr.Thread(target=self.position_receiver,)
        data_stream.start()

    def position_receiver(self):
        while self.experiment_running:
            topic = self.position_comm.socket.recv_string()
            data = self.position_comm.socket.recv_pyobj()

            self.fish_data.append(data)

            if not np.isnan(data[0]):
                self.last_fish_present = time.time()

            # trim lists
            if len(self.fish_data) >= self.max_buffer:
                self.fish_data = self.fish_data[-self.max_buffer//2:]

    def centering_calibration(self):
        while not self.experiment_finished:
            topic = self.stytra_cam_output_port.socket.recv_string()
            if topic == 'calibrationStimulus':
                ## this will be a toggled string on/off
                msg = self.stytra_cam_output_port.socket.recv_pyobj()[0]
                toggle_direction = msg.split('_')[-1]

                if toggle_direction == 'on':
                    messenger.send('calibration_stimulus', [True])
                elif toggle_direction == 'off':
                    messenger.send('calibration_stimulus', [False])
            else:
                ## this will be images
                image = utils.img_receiver(self.stytra_cam_output_port.socket)
                if topic == 'calibration':
                    try:
                        proj_to_camera, camera_to_proj = calibration.StimulusCalibrator(image).transforms()
                        calibration.save_params(proj_to_camera, camera_to_proj, self.rig_number)
                        print('CALIBRATION SAVED: ', proj_to_camera)

                    except Exception as e:
                        print('failed to calibrate', e)

                elif topic == 'centering':
                    image -= 3
                    image[image < 0] = 0
                    image = np.array(image)

                    def draw(event, x, y, flags, params):
                        if event==1:
                            cv2.line(image, pt1=(x,y), pt2=(x,y), color=(255,255,255), thickness=3)
                            cv2.destroyAllWindows()
                    cv2.namedWindow('centerWindow')
                    cv2.setMouseCallback('centerWindow', draw)

                    # opencv windows like to pop up in the background, this is hacky but brings it to front
                    centering_window = gw.getWindowsWithTitle('centerWindow')[0]
                    centering_window.minimize()
                    centering_window.restore()
                    centering_window.maximize()

                    cv2.imshow('centerWindow', image)
                    cv2.waitKey(0)
                    # lots of destroying the window so opencv cant stick around :)
                    cv2.destroyAllWindows()

                    # we drew something max val on an image that contained no max vals, now we grab it
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(image)
                    self.centered_pt = np.array([max_loc[0], max_loc[1]])
                    pos = (self.centered_pt[1], self.centered_pt[0])
                    try:
                        print(f'raw: {self.centered_pt} texture:  {cv2.transform(np.reshape(pos, (1, 1, 2)), self.cam2proj)[0][0]} card: {self.position_transformer(pos[0], pos[1])}')
                    except Exception as e:
                        print(f'raw {self.centered_pt}' ,e)

    # use the cam2proj
    def position_transformer(self, x, y):
        # swap order to flip xy
        pos = np.array([x, y])
        conv_pt = cv2.transform(np.reshape(pos, (1, 1, 2)), self.cam2proj)[0][0]

        a = conv_pt[0]
        b = conv_pt[1]

        x = -1 * ((a / self.defaults['window_size'][0]) - 0.5)
        y = -1 * ((b / self.defaults['window_size'][1]) - 0.5)

        return x, y

    def end_experiment(self):
        print('experiment finished')
        curr_t = time.time()
        self.timing_comm.socket.send_string('time', zmq.SNDMORE)
        self.timing_comm.socket.send_pyobj([curr_t - self.init_time + 3, curr_t - self.init_time])
        messenger.send('end_experiment')

        self.experiment_finished = True
        self.experiment_running = False

        sys.exit()

    def stim_sequencer(self):
        pass

class CenterClickTestingProtocol(BaseProtocol):
    '''
    this testing protocol lets you click to move a circle to your click point
    '''
    def __init__(self, *args, **kwargs):
        self.last_stim = 9
        self.x, self.y = [0,0]
        super().__init__(*args, **kwargs)

    def run_experiment(self):
        super().run_experiment()
        stim = [0,
                {'stim_type' : 's', 'velocity' : 0, 'angle' : 0, 'texture' : textures.CircleGrayTex(circle_radius=3),
                 }]
        messenger.send('stimulus', [stim])
        self.show_tracking()

    def position_receiver(self):
        while self.experiment_running:
            topic = self.position_comm.socket.recv_string()
            self.data = self.position_comm.socket.recv_pyobj()
            self.show_tracking()

    def show_tracking(self):
        if self.x != self.centered_pt[0] and self.y != self.centered_pt[1]:
            self.x, self.y = self.centered_pt
            x,y = self.position_transformer(self.x, self.y)
            messenger.send('stimulus_update', [[x, y]])


class FishTrackerTestingProtocol(CenterClickTestingProtocol):
    '''
    this one moves a circle around under the fish
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def show_tracking(self):
        if not np.isnan(self.data[0]):
            _x = self.data[1]
            _y = self.data[0]
            x, y = self.position_transformer(_x, _y)
            messenger.send('stimulus_update', [[x, y, 0]])


class OpenLoopProtocol(BaseProtocol):
    def __init__(self, *args, **kwargs):
        self.current_stim_id = 0
        super().__init__(*args, **kwargs)

    def run_experiment(self):
        super().run_experiment()

        curr_t = time.time()
        self.timing_comm.socket.send_string('time', zmq.SNDMORE)
        self.timing_comm.socket.send_pyobj([curr_t - self.init_time + 3 + np.sum(self.stimuli.duration.values), curr_t - self.init_time])

        self.stim_sequencer()

    def stim_sequencer(self):
        if self.current_stim_id > len(self.stimuli) - 1:
            self.experiment_finished = True
            self.end_experiment()
            # do some finishing here

        stimulus = self.stimuli.loc[self.current_stim_id]
        stim = [self.current_stim_id, stimulus]
        messenger.send('stimulus', [stim])
        wait_fxn = tr.Thread(target=self.time_delay, args=(stimulus.duration,))
        wait_fxn.start()
        wait_fxn.join()

    def time_delay(self, duration):
        init_time = time.time()
        while time.time() - init_time <= duration - 0.05:
            pass
        self.current_stim_id += 1
        self.stim_sequencer()


class ClosedLoopProtocol(BaseProtocol):
    def __init__(self, *args, **kwargs):
        # update stytras timer this often (in seconds)
        # if this is too fast stytra gets wrecked
        self.t_update_frequency = 1

        self.current_stim_id = -1
        self.stimulating = False

        super().__init__(*args, **kwargs)

    def run_experiment(self):
        self.filestream = utils.updated_saving(self.defaults['save_path'])


        # recenter the fish if she's gone more than this time
        self.missing_fish_t = self.defaults['missing_fish_t']

        # units in camera XY pixels fish must be within center to trigger a trial
        self.min_fish_dst_to_center = self.defaults['min_fish_dst_to_center']
        self.xy_thresh = 35
        self.theta_thresh = 8.5

        self.last_t_update = 0
        self.last_message = None

        self.current_stim = {'stim_type' : None, 'angle' : None, }

        super().run_experiment()

        curr_t = time.time()
        self.timing_comm.socket.send_string('time', zmq.SNDMORE)
        self.timing_comm.socket.send_pyobj([curr_t - self.init_time + 3 + np.sum(self.stimuli.duration.values), curr_t - self.init_time])

    def send_centering(self):
        cali_pos = self.position_transformer(self.centered_pt[0], self.centered_pt[1])
        if self.defaults['radial_centering']:
            centering_stimulus = [-1, {'stim_type': 'centering', 'type': 'radial', 'velocity': 0, 'angle' : 0, 'center_x': cali_pos[0],
                                       'center_y': cali_pos[1]}]
        else:
            centering_stimulus = [-1, {'stim_type': 'centering', 'type': 'static', 'velocity': 0, 'angle' : 0, 'center_x': cali_pos[0],
                                       'center_y': cali_pos[1]}]

        messenger.send('stimulus', [centering_stimulus])
        self.save(centering_stimulus, self.fish_data[-1][0], self.fish_data[-1][1], self.fish_data[-1][2])

    def save(self, stim, x, y, theta):
        self.filestream.write("\n")
        t = time.time() - self.init_time
        if 'duration' in stim[1]:
            dur = stim[1]['duration']
        else:
            dur = 99
        if 'stationary_time' in stim[1]:
            stat = stim[1]['stationary_time']
        else:
            stat = 0
        self.filestream.write(f"{t}_{self.current_stim_id}_{stim[1]['stim_type']}_{stim[1]['angle']}_{dur}_{stat}_{x}_{y}_{theta}")
        self.filestream.flush()

    def update_time(self):
        curr_t = time.time()
        if curr_t - self.last_t_update >= self.t_update_frequency:

            self.timing_comm.socket.send_string('time', zmq.SNDMORE)
            if self.current_stim_id != -1:
                self.timing_comm.socket.send_pyobj(
                    [(curr_t - self.init_time) + 3 + np.sum(
                        self.stimuli.duration.values[self.current_stim_id:]), (curr_t - self.init_time)])
            else:
                self.timing_comm.socket.send_pyobj(
                    [(curr_t - self.init_time) + 3 + np.sum(
                        self.stimuli.duration.values), (curr_t - self.init_time)])
            self.last_t_update = curr_t

    def position_receiver(self):
        while self.experiment_running:
            topic = self.position_comm.socket.recv_string()
            data = self.position_comm.socket.recv_pyobj()

            self.fish_data.append(data)

            if not np.isnan(data[0]):
                self.last_fish_present = time.time()

            # trim lists
            if len(self.fish_data) >= self.max_buffer:
                self.fish_data = self.fish_data[-self.max_buffer//2:]

            self.stim_sequencer()

    def stim_sequencer(self):
        # This is called every time new data arrives

        if time.time() - self.last_fish_present >= self.missing_fish_t or np.sum(np.isnan(np.array(self.fish_data)[:, 0][-20:])) >= 7: ##FISH LESS THAN 5 FRAMES:
            # RECENTER THE FISH #
            if self.last_message != f"centering_at_{self.centered_pt}":
                self.send_centering()
                self.last_message = f"centering_at_{self.centered_pt}"
                print('beep boop we center')

            self.stimulating = False
            self.update_time()

        else:
            data = np.array(self.fish_data)

            self._x = data[:, 0][~np.isnan(data[:,0])]
            self._y = data[:, 1][~np.isnan(data[:,1])]

            self.theta = data[:, 2][~np.isnan(data[:, 2])]

            dst_center = np.linalg.norm(np.array([self._x[-1], self._y[-1]]) - np.array(self.centered_pt))
            # print(dst_center, self.stimulating)

            if not dst_center <= self.min_fish_dst_to_center and not self.stimulating:
                # RECENTER THS FISH #
                if self.last_message != f"centering_at_{self.centered_pt}":
                    self.send_centering()
                    self.last_message = f"centering_at_{self.centered_pt}"

                self.stimulating = False
                self.update_time()

            else:
                # IF YOU MAKE IT TO HERE YOUR SHOWING STIMULI #
                if not self.stimulating:
                    self.current_stim_id += 1

                    if self.current_stim_id > len(self.stimuli) - 1:
                        self.end_experiment()

                    self.current_stim = self.stimuli.loc[self.current_stim_id]

                    messenger.send('stimulus', [[self.current_stim_id, self.current_stim]])
                    x, y = self.position_transformer(self._y[-1], self._x[-1])
                    theta = degrees(utils.reduce_to_pi(np.nanmean(self.theta[-5:])))
                    messenger.send('stimulus_update', [[x, y, theta]])
                    self.last_update_time = time.time()
                    # self.save([self.current_stim_id, self.current_stim], self._x[-1], self._y[-1], self.theta[-1])

                    self.last_message = 'some_stimmin'

                    self.stimulating = True
                    self.stim_start = time.time()

                if self.stimulating and time.time() - self.stim_start <= self.current_stim.duration:
                    # this is where we'll do the updating of xytheta
                    XCHECK = abs(np.nanmean(self._x[-30:]) - self._x[-1]) >= self.xy_thresh
                    YCHECK = abs(np.nanmean(self._y[-30:]) - self._y[-1]) >= self.xy_thresh
                    XYCHECK = (XCHECK or YCHECK) and not self.current_stim.stim_type == 's'

                    THETACHECK = (abs(np.nanmean(self.theta[-30:]) - np.nanmean(self.theta[-5:])) / abs(np.nanmean(self.theta[-8:]))) * 100 >= self.theta_thresh
                    # print('THETA ', THETACHECK , (abs(np.nanmean(self.theta[-30:]) - self.theta[-1]) / abs(self.theta[-1])) * 100)
                    if time.time() - self.last_update_time >= 0.1:
                        if XYCHECK and THETACHECK:
                            x, y = self.position_transformer(self._y[-1], self._x[-1])
                            theta = degrees(utils.reduce_to_pi(np.nanmean(self.theta[-8:])))
                            messenger.send('stimulus_update', [[x, y, theta]])
                            # self.save([self.current_stim_id, self.current_stim], self._x[-1], self._y[-1], self.theta[-1])

                            self.last_update_time = time.time()
                        elif XYCHECK:
                            x, y = self.position_transformer(self._y[-1], self._x[-1])
                            messenger.send('stimulus_update', [tuple([x, y])])
                            # self.save([self.current_stim_id, self.current_stim], self._x[-1], self._y[-1], self.theta[-1])

                            self.last_update_time = time.time()

                        elif THETACHECK:
                            theta = degrees(utils.reduce_to_pi(np.nanmean(self.theta[-8:])))
                            messenger.send('stimulus_update', [theta])
                            # self.save([self.current_stim_id, self.current_stim], self._x[-1], self._y[-1], self.theta[-1])
                            self.last_update_time = time.time()


                else:
                    self.stimulating = False
        self.save([self.current_stim_id, self.current_stim], self.fish_data[-1][0], self.fish_data[-1][1], self.fish_data[-1][2])
