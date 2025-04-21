'''
this setup uses the stytra package for fish tracking:
https://github.com/portugueslab/stytra
'''
import zmq
import qdarkstyle
import sys

import numpy as np
import pyqtgraph as pg

from pathlib import Path

# GUI imports
from stytra.stimulation.stimuli import Stimulus
from stytra.experiments.tracking_experiments import TrackingExperiment
from stytra.gui.container_windows import TrackingExperimentWindow
from stytra.gui.camera_display import CameraViewFish, CameraViewEyeFish, EyeTrackingSelection, TailTrackingSelection, EyeTailTrackingSelection, SingleLineROI
from stytra.gui.camera_display import _tail_points_from_coords as tail_points
from stytra.gui.buttons import IconButton
from stytra.gui.multiscope import MultiStreamPlot
from stytra import Protocol

from lightparam.gui import ControlCombo

from PyQt5.QtWidgets import QToolButton, QApplication, QWidget, QVBoxLayout
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize

from pandastim.utils import Publisher, port_provider


# stuff to run a stytra window and communicate with pandas
class TimeUpdater(Stimulus):
    """
    uses the stimulus framework from stytra to update timing externally
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # sends a signal out -- linked to the play button
        self.external_starter = 0
        self.go = None

        # This takes in timing information from external protocol
        self.timing = None
        # initializes with some bogus duration as a buffer
        self.duration = 5

        # initializes the variables to measure the time
        self.sent_times = [0, 0]
        self.exp_max = 99999999
        self.exp_elapsed = 0

    # connects to stytra to get the internal experiment parameters from stytra
    def initialise_external(self, experiment):
        super().initialise_external(experiment)
        try:
            stims_socket = self._experiment.go_socket
            sending_context = zmq.Context()
            self.go = sending_context.socket(zmq.REQ)
            self.go.connect('tcp://localhost:' + str(stims_socket))
        except AttributeError:
            pass

        try:
            time_socket = self._experiment.timing_socket
            context = zmq.Context()
            self.timing = context.socket(zmq.SUB)
            self.timing.setsockopt(zmq.SUBSCRIBE, b'time')
            self.timing.connect("tcp://localhost:" + str(time_socket))
            print('timing socket connected on ', time_socket)
        except AttributeError:
            print('error initializing timing socket')

    def update(self):

        # if condition met, update duration
        # this only runs the first time
        if self.external_starter == 0:
            self.go.send_string('True')
            self.external_starter = 1
        try:
            # check for a message, this will not block
            times_t = self.timing.recv_string(flags=zmq.NOBLOCK)
            self.sent_times = self.timing.recv_pyobj(flags=zmq.NOBLOCK)
            self.exp_max = self.sent_times[0]
            self.exp_elapsed = self.sent_times[1]

            self.duration = np.float64(self.exp_max)

        except zmq.Again:
            pass

        data = np.array(self._experiment.estimator.get_position())
        self._experiment.pstim_pub.socket.send_string('pos')
        self._experiment.pstim_pub.socket.send_pyobj(data)



class StytraDummy(Protocol):
    """
    generic blank Stytra Protocol
    """
    name = "dummy"

    def __init__(self, ):
        super().__init__()

    def get_stim_sequence(self):
        return [TimeUpdater()]


class LocalIconButton(QToolButton):
    def __init__(self, icon_name="", action_name="", size=[48, 32], *args, **kwargs):
        super().__init__(*args, **kwargs)

        prePath = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources')

        self.icon = QIcon(prePath.joinpath(icon_name + '.jpg').as_posix())
        self.setIcon(self.icon)
        self.setToolTip(action_name)
        self.setFixedSize(QSize(size[0], size[0]))
        self.setIconSize(QSize(size[0], size[0]))


class ExternalCameraDisplay(CameraViewFish):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.centeringButton = LocalIconButton(
            icon_name="CenteringButton", action_name="choose new centerpoint"
        )
        self.centeringButton.clicked.connect(self.center_calibrator)
        self.layout_control.addWidget(self.centeringButton)

        self.projectionCalibration = LocalIconButton(
            icon_name="CalibrationButton", action_name="Calibrate Projection"
        )
        self.projectionCalibration.clicked.connect(self.stimulus_calibration)
        self.layout_control.addWidget(self.projectionCalibration)

        self.calibrationStimulus = LocalIconButton(
            icon_name="CalibrationMode", action_name="swap to calibration stimulus"
        )
        self.calibrationStimulus.clicked.connect(self.calibration_stimulus)
        self.layout_control.addWidget(self.calibrationStimulus)

        self.calibration_toggle = 0

        image_sock = self.experiment.return_image_socket()
        if image_sock is not None:
            self.centering_socket_number = image_sock
            self.centering_context = zmq.Context()
            self.centering_socket = self.centering_context.socket(zmq.PUB)
            self.centering_socket.bind(str("tcp://*:") + str(self.centering_socket_number))


    def center_calibrator(self):
        print('centering')
        topic = 'centering'
        self.msg_sender(sock=self.centering_socket, img=self.image_item.image, string=topic, image=True)

    def stimulus_calibration(self):
        print('calibrating')
        topic = 'calibration'
        self.msg_sender(sock=self.centering_socket, img=self.image_item.image, string=topic, image=True)

    def calibration_stimulus(self):
        if self.calibration_toggle == 0:
            self.calibration_toggle = 1
            status = 'calibration_stimulus_on'
        elif self.calibration_toggle == 1:
            self.calibration_toggle = 0
            status = 'calibration_stimulus_off'

        topic = 'calibrationStimulus'

        if self.calibration_toggle == 0:
            self.msg_sender(sock=self.centering_socket, img=status, string=topic, image=False)

        if self.calibration_toggle == 1:
            self.msg_sender(sock=self.centering_socket, img=status, string=topic, image=False)

    @staticmethod
    def msg_sender(sock, img, string, image=True):
        if image:
            my_msg = dict(dtype=str(img.dtype), shape=img.shape)
            sock.send_string(string, zmq.SNDMORE)
            sock.send_json(my_msg, zmq.SNDMORE)
            return sock.send(img)
        else:
            sock.send_string(string, zmq.SNDMORE)
            return sock.send_pyobj([img])

    def retrieve_image(self):
        super().retrieve_image()

        if (
            len(self.experiment.acc_tracking.stored_data) == 0
            or self.current_image is None
        ):
            return

        current_data = self.experiment.acc_tracking.values_at_abs_time(
            self.current_frame_time
        )
        n_fish = self.tracking_params.n_fish_max

        n_data_per_fish = (
            len(current_data) - 1
        ) // n_fish  # the first is time, the last is area
        n_points_tail = self.tracking_params.n_segments
        try:
            retrieved_data = np.array(
                current_data[:-1]  # the -1 if for the diagnostic area
            ).reshape(n_fish, n_data_per_fish)
            valid = np.logical_not(np.all(np.isnan(retrieved_data), 1))
            self.points_fish.setData(
                x=retrieved_data[valid, 2], y=retrieved_data[valid, 0]
            )
            if n_points_tail:
                tail_len = (
                    self.tracking_params.tail_length / self.tracking_params.n_segments
                )
                ys, xs = tail_points(retrieved_data, tail_len, n_points_tail)
                self.lines_fish.setData(y=xs, x=ys)
        except ValueError as e:
            pass

class ExternalCameraDisplay_eyefish(CameraViewEyeFish):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.centeringButton = LocalIconButton(
            icon_name="CenteringButton", action_name="choose new centerpoint"
        )
        self.centeringButton.clicked.connect(self.center_calibrator)
        self.layout_control.addWidget(self.centeringButton)

        self.projectionCalibration = LocalIconButton(
            icon_name="CalibrationButton", action_name="Calibrate Projection"
        )
        self.projectionCalibration.clicked.connect(self.stimulus_calibration)
        self.layout_control.addWidget(self.projectionCalibration)

        self.calibrationStimulus = LocalIconButton(
            icon_name="CalibrationMode", action_name="swap to calibration stimulus"
        )
        self.calibrationStimulus.clicked.connect(self.calibration_stimulus)
        self.layout_control.addWidget(self.calibrationStimulus)

        self.calibration_toggle = 0

        image_sock = self.experiment.return_image_socket()
        if image_sock is not None:
            self.centering_socket_number = image_sock
            self.centering_context = zmq.Context()
            self.centering_socket = self.centering_context.socket(zmq.PUB)
            self.centering_socket.bind(str("tcp://*:") + str(self.centering_socket_number))


    def center_calibrator(self):
        print('centering')
        topic = 'centering'
        self.msg_sender(sock=self.centering_socket, img=self.image_item.image, string=topic, image=True)

    def stimulus_calibration(self):
        print('calibrating')
        topic = 'calibration'
        self.msg_sender(sock=self.centering_socket, img=self.image_item.image, string=topic, image=True)

    def calibration_stimulus(self):
        if self.calibration_toggle == 0:
            self.calibration_toggle = 1
            status = 'calibration_stimulus_on'
        elif self.calibration_toggle == 1:
            self.calibration_toggle = 0
            status = 'calibration_stimulus_off'

        topic = 'calibrationStimulus'

        if self.calibration_toggle == 0:
            self.msg_sender(sock=self.centering_socket, img=status, string=topic, image=False)

        if self.calibration_toggle == 1:
            self.msg_sender(sock=self.centering_socket, img=status, string=topic, image=False)

    @staticmethod
    def msg_sender(sock, img, string, image=True):
        if image:
            my_msg = dict(dtype=str(img.dtype), shape=img.shape)
            sock.send_string(string, zmq.SNDMORE)
            sock.send_json(my_msg, zmq.SNDMORE)
            return sock.send(img)
        else:
            sock.send_string(string, zmq.SNDMORE)
            return sock.send_pyobj([img])

    def retrieve_image(self):
        super().retrieve_image()
        if (
            len(self.experiment.acc_tracking.stored_data) == 0
            or self.current_image is None
        ):
            return

        current_data = self.experiment.acc_tracking.values_at_abs_time(
            self.current_frame_time
        )
        n_fish = self.tracking_params.n_fish_max

        n_data_per_fish = (
            len(current_data) - 1
        ) // n_fish  # the first is time, the last is area
        n_points_tail = self.tracking_params.n_segments
        try:
            retrieved_data = np.array(
                current_data[:-1]  # the -1 if for the diagnostic area
            ).reshape(n_fish, n_data_per_fish)
            valid = np.logical_not(np.all(np.isnan(retrieved_data), 1))
            self.points_fish.setData(
                x=retrieved_data[valid, 2], y=retrieved_data[valid, 0]
            )
            if n_points_tail:
                tail_len = (
                    self.tracking_params.tail_length / self.tracking_params.n_segments
                )
                ys, xs = tail_points(retrieved_data, tail_len, n_points_tail)
                self.lines_fish.setData(y=xs, x=ys)
        except ValueError as e:
            pass


class ExternalCameraDisplay_embed(TailTrackingSelection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.centeringButton = LocalIconButton(
            icon_name="CenteringButton", action_name="choose new centerpoint"
        )
        self.centeringButton.clicked.connect(self.center_calibrator)
        self.layout_control.addWidget(self.centeringButton)

        self.projectionCalibration = LocalIconButton(
            icon_name="CalibrationButton", action_name="Calibrate Projection"
        )
        self.projectionCalibration.clicked.connect(self.stimulus_calibration)
        self.layout_control.addWidget(self.projectionCalibration)

        self.calibrationStimulus = LocalIconButton(
            icon_name="CalibrationMode", action_name="swap to calibration stimulus"
        )
        self.calibrationStimulus.clicked.connect(self.calibration_stimulus)
        self.layout_control.addWidget(self.calibrationStimulus)

        self.calibration_toggle = 0

        image_sock = self.experiment.return_image_socket()
        if image_sock is not None:
            self.centering_socket_number = image_sock
            self.centering_context = zmq.Context()
            self.centering_socket = self.centering_context.socket(zmq.PUB)
            self.centering_socket.bind(str("tcp://*:") + str(self.centering_socket_number))        


    def center_calibrator(self):
        print('centering')
        topic = 'centering'
        self.msg_sender(sock=self.centering_socket, img=self.image_item.image, string=topic, image=True)

    def stimulus_calibration(self):
        print('calibrating')
        topic = 'calibration'
        self.msg_sender(sock=self.centering_socket, img=self.image_item.image, string=topic, image=True)

    def calibration_stimulus(self):
        if self.calibration_toggle == 0:
            self.calibration_toggle = 1
            status = 'calibration_stimulus_on'
        elif self.calibration_toggle == 1:
            self.calibration_toggle = 0
            status = 'calibration_stimulus_off'

        topic = 'calibrationStimulus'

        if self.calibration_toggle == 0:
            self.msg_sender(sock=self.centering_socket, img=status, string=topic, image=False)

        if self.calibration_toggle == 1:
            self.msg_sender(sock=self.centering_socket, img=status, string=topic, image=False)

    def initialise_roi(self, roi):
        """ROI is initialised separately, so it can first be defined in the
        child __init__.

        Parameters
        ----------

        Returns
        -------

        """
        # Add ROI to image and connect it to the function for updating
        # the relative params:
        self.display_area.addItem(roi)
        roi.sigRegionChanged.connect(self.set_pos_from_roi)

    @staticmethod
    def msg_sender(sock, img, string, image=True):
        if image:
            my_msg = dict(dtype=str(img.dtype), shape=img.shape)
            sock.send_string(string, zmq.SNDMORE)
            sock.send_json(my_msg, zmq.SNDMORE)
            return sock.send(img)
        else:
            sock.send_string(string, zmq.SNDMORE)
            return sock.send_pyobj([img])

    def retrieve_image(self):
        super().retrieve_image()

        if self.current_image is None:
            return

        # Get data from queue(first is timestamp)
        if len(self.experiment.acc_tracking.stored_data) > 1:
            #TAIL STUFF
            # To match tracked points and frame displayed looks for matching
            # timestamps from the two different queues:
            retrieved_data = self.experiment.acc_tracking.values_at_abs_time(
                self.current_frame_time
            )

            # Check for data to be displayed:
            # Retrieve tail angles from tail
            angles = [
                getattr(retrieved_data, "theta_{:02d}".format(i))
                for i in range(self.tail_params.n_output_segments)
            ]
            # Get tail position and length from the parameters:
            (start_y, start_x), (tail_len_y, tail_len_x) = self.tail_dims()
            tail_length = np.sqrt(tail_len_x ** 2 + tail_len_y ** 2)

            # Get segment length:
            tail_segment_length = tail_length / (len(angles))
            points = [np.array([start_x, start_y])]

            # Calculate tail points from angles and position:
            for angle in angles:
                points.append(
                    points[-1]
                    + tail_segment_length * np.array([np.cos(angle), np.sin(angle)])
                )
            points = np.array(points)
            self.curve_tail.setData(x=points[:, 1], y=points[:,0])
           


class ExternalTrackingExperimentWindow(TrackingExperimentWindow):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.camera_display = ExternalCameraDisplay_eyefish(experiment=kwargs["experiment"])

        self.monitoring_widget = QWidget()
        self.monitoring_layout = QVBoxLayout()
        self.monitoring_widget.setLayout(self.monitoring_layout)

        self.stream_plot = MultiStreamPlot(experiment=self.experiment)

        self.monitoring_layout.addWidget(self.stream_plot)

        self.extra_widget = (self.experiment.pipeline.extra_widget(
            self.experiment.acc_tracking)
                             if self.experiment.pipeline.extra_widget is not None
                             else None)
        # Display dropdown
        self.drop_display = ControlCombo(
            self.experiment.pipeline.all_params["diagnostics"],
            "image")

        if hasattr(self.camera_display, "set_pos_from_tree"):
            self.drop_display.control.currentTextChanged.connect(
                self.camera_display.set_pos_from_tree)

        # Tracking params button:
        self.button_tracking_params = IconButton(
            icon_name="edit_tracking", action_name="Change tracking parameters"
        )
        self.button_tracking_params.clicked.connect(self.open_tracking_params_tree)

        self.camera_display.layout_control.addStretch(10)
        self.camera_display.layout_control.addWidget(self.drop_display)
        self.camera_display.layout_control.addWidget(self.button_tracking_params)
        self.track_params_wnd = None

        self.status_display.addMessageQueue(self.experiment.frame_dispatcher.message_queue)


class ExternalTrackingExperiment(TrackingExperiment):
    def __init__(self, ports, automated=False,
                 *args,
                 **kwargs
                 ):
        self.need_image = False

        self.image_socket = ports['image_socket']
        self.go_socket = ports['go_socket']
        self.timing_socket = ports['timing_socket']
        self.saving_socket = ports['saving_socket']
        self.pstim_pub = Publisher(str(ports['tracking_socket']))

        self.automated = automated

        self.calibrator = None

        super().__init__(*args, **kwargs)

    def get_image(self):
        return self.frame_dispatcher[0]

    def return_image_socket(self):
        return self.image_socket

    def end_protocol(self, save=True):
        super().end_protocol()

    def make_window(self):
        self.window_main = ExternalTrackingExperimentWindow(experiment=self)
        self.window_main.construct_ui()
        self.initialize_plots()
        self.window_main.show()
        self.restore_window_state()

        if self.automated:
            self.start_protocol()

    def show_stimulus_screen(self, full_screen=False):
        pass


def stytra_container(ports, camera_rot=0, roi=None, savedir=None,):
    """
    package the stytra classes together and run as a pyqt application
    uses ZMQ sockets to communicate around
    :param image_socket: for sending raw images for calibration or grabbing XY positions
    :param go_button_socket: links the stytra go button
    :param time_socket: socket for the timing information
    :param camera_rot: rotates the camera image (rig specific)
    :param roi: controls camera field of view
    :param savedir: initializes stytra saving path
    """
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)

    if roi is None:
        roi = [0, 0, 1120, 1120]

    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    protocol = StytraDummy()
    exp = ExternalTrackingExperiment(protocol=protocol, app=app, dir_save=savedir,
                                     tracking=dict(method='fish_eye', embedded=True, estimator="position"),
                                     camera=dict(type='svs', min_framerate=155, rotation=camera_rot, roi=roi),
                                     ports=ports
                                     )

    exp.start_experiment()
    app.exec_()


if __name__ == '__main__':

    _ports = {}
    keys = ['image_socket', 'go_socket', 'timing_socket', 'saving_socket', 'tracking_socket']
    for key in keys:
        _ports[key] = port_provider()

    stytra_container(ports=_ports)
