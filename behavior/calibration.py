import numpy as np

import cv2
import zmq
import sys

from pathlib import Path

from pandastim import utils
from pandastim.stimuli import textures


class CalibrationException(Exception):
    """
    Blob detection for calibration failed
    """
    pass


class StimulusCalibrator:
    def __init__(self, camera_img, manual = False, camera_pts = (None, None, None)):

        self.camera_img = camera_img - 3
        self.projected_pts = self.get_proj_pts()
        self.projected_pts = self.projected_pts[np.argsort(self._find_angles(self.projected_pts)), :]
        if not manual:
            self.camera_pts = self._find_triangle(self.camera_img)
        else:
            self.camera_pts = camera_pts[np.argsort(StimulusCalibrator._find_angles(camera_pts)), :]

    @staticmethod
    def get_proj_pts():
        cali_params = utils.get_calibration_params()
        if cali_params is None:
            return textures.CalibrationTriangles().projct_coords()
        else:
            return textures.CalibrationTriangles(tri_size=cali_params['tri_size'],
                                                circle_radius=cali_params['circle_radius'],
                                                x_offset=cali_params['x_off'],
                                                y_offset=cali_params['y_off']).projct_coords()


    def transforms(self):
        x_proj = np.vstack([self.projected_pts.T, np.ones(3)])
        x_cam = np.vstack([self.camera_pts.T, np.ones(3)])
        proj_to_camera = self.camera_pts.T @ np.linalg.inv(x_proj)
        camera_to_proj = self.projected_pts.T @ np.linalg.inv(x_cam)

        print('cam coords:', self.camera_pts)
        print('projected in cam coords:', cv2.transform(np.reshape(self.projected_pts, (3, 1, 2)), proj_to_camera))
        return proj_to_camera, camera_to_proj

    def return_means(self):
        return np.mean(self.camera_pts, axis=0)

    @staticmethod
    def _find_triangle(image, blob_params=None):
        blob_params = cv2.SimpleBlobDetector_Params()
        blob_params.maxThreshold = 256;
        if blob_params is None:
            blobdet = cv2.SimpleBlobDetector_create()
        else:
            blobdet = cv2.SimpleBlobDetector_create(blob_params)

        scaled_im = 255 - (image.astype(np.float32) * 255 / np.max(image)).astype(
            np.uint8
        )
        keypoints = blobdet.detect(scaled_im)
        if len(keypoints) != 3:
            raise CalibrationException("3 points for calibration not found")
        kps = np.array([k.pt for k in keypoints])

        # Find the angles between the points
        # and return the points sorted by the angles

        return kps[np.argsort(StimulusCalibrator._find_angles(kps)), :]

    @staticmethod
    def _find_angles(kps):
        angles = np.empty(3)
        for i, pt in enumerate(kps):
            pt_prev = kps[(i - 1) % 3]
            pt_next = kps[(i + 1) % 3]
            # angles are calculated from the dot product
            angles[i] = np.abs(
                np.arccos(
                    np.sum((pt_prev - pt) * (pt_next - pt)) / np.product(
                        [np.sqrt(np.sum((pt2 - pt) ** 2)) for pt2 in [pt_prev, pt_next]]
                    )
                )
            )
        return angles


def save_params(proj2cam, cam2proj, rig_number):
    parent_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params')
    np.save(parent_path.joinpath(f'rig_{rig_number}_proj2cam.npy'), proj2cam)
    np.save(parent_path.joinpath(f'rig_{rig_number}_cam2proj.npy'), cam2proj)


def load_params(rig_number):
    parent_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params')
    proj2cam = np.load(parent_path.joinpath(f'rig_{rig_number}_proj2cam.npy'))
    cam2proj = np.load(parent_path.joinpath(f'rig_{rig_number}_cam2proj.npy'))
    print(f"loading from: {parent_path.joinpath(f'rig_{rig_number}_cam2proj.npy')}")
    return proj2cam, cam2proj

def save_centers(centered_pt, centered_theta, rig_number):
    parent_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params')
    np.save(parent_path.joinpath(f'rig_{rig_number}_centers.npy'), [centered_pt[0], centered_pt[1], centered_theta])

def load_centers(rig_number):
    parent_path = Path(sys.executable).parents[0].joinpath(r'Lib\site-packages\pandastim\resources\params')
    centers = np.load(parent_path.joinpath(f'rig_{rig_number}_centers.npy'))
    return (centers[0], centers[1]), centers[2]

def calibrator(input_socket, point_dump):
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.SUBSCRIBE, b'calibration')
    socket.connect(str("tcp://localhost:") + str(input_socket))

    outputs = utils.img_receiver(socket)
    img = outputs
    print('got image')
    # mywind = gw.getWindowsWithTitle('calibrator_triangle')[0]
    # mywind.close()
    proj_pts = point_dump.get()
    proj_to_camera, camera_to_proj = StimulusCalibrator(img, proj_pts).transforms()
    parentPath = Path(__file__).parent.resolve()
    np.save(parentPath.joinpath('_cam2proj.npy'), camera_to_proj)
    np.save(parentPath.joinpath('_proj2cam.npy'), proj_to_camera)
