import matplotlib.pyplot
import numpy as np
import cv2, os, threading, time, logging
import cppimport, pybind11
import ctypes as ct

from pandas.io.sas.sas_constants import file_type_offset
#from stytra.hardware.video.cameras.interface import Camera

class CameraError(object):
    SV_ERROR_TIMEOUT = -1011

class InterfaceType(object):
    GIG_E = 0
    USB3 = 1
    CAMERA_LINK = 2

class InterfaceName(object):
    GIG_E = "Gig_E"
    USB3 = "USB3"
    CAMERA_LINK= "CameraLink"

class TriggerMode(object):
    OFF = 0
    ON = 1

class CameraSettingDataType(object):
    INT = 1
    FLOAT = 2
    ENUM = 3
    BOOL = 4
    STR = 5

class CameraSettings(object):
    ACQUISITION_TIMEOUT = "AcquisitionTimeout"
    CHANNELS = "Channels"
    EXPOSURE_TIME = "ExposureTime"
    HEIGHT = "Height"
    TRIGGER_MODE = "TriggerMode"
    WIDTH = "Width"

    """
    Settings of type ENUM
    """
    def get_enums(self):
        return [self.TRIGGER_MODE]

    """
    Settings of type FLOAT
    """
    def get_floats(self):
        return [self.EXPOSURE_TIME]

    """
    Settings of type INT
    """
    def get_ints(self):
        return [self.HEIGHT, self.WIDTH]

class SV_DEVICE_ACCESS_FLAGS(ct.c_uint32):
    UNKNOWN = 0
    NONE = 1
    READONLY = 2
    CONTROL = 3
    EXCLUSIVE = 4

class SV_ACQ_QUEUE_TYPE(ct.c_uint32):
    INPUT_TO_OUTPUT = 0
    OUTPUT_DISCARD = 1
    ALL_TO_INPUT = 2
    UNQUEUED_TO_INPUT = 3
    ALL_DISCARD = 4

class SV_ACQ_START_FLAGS(ct.c_uint32):
    DEFAULT = 0

class SV_ACQ_STOP_FLAGS(ct.c_uint32):
    DEFAULT = 0
    KILL = 1

class SV_FEATURE_INFO(ct.Structure):
    _fields_ = [
        ("type", ct.c_uint8),
        ("name", ct.c_char * 512),  # Assuming SV_STRING_SIZE = 256
        ("node", ct.c_char * 512),
        ("displayName", ct.c_char *512),
        ("toolTip", ct.c_char * 512),
        ("level", ct.c_uint8),
        ("visibility", ct.c_uint8),
        ("isImplemented", ct.c_uint8),
        ("isAvailable", ct.c_uint8),
        ("isLocked", ct.c_uint8),
        # Feature-specific fields
        ("intMin", ct.c_int64),
        ("intMax", ct.c_int64),
        ("intInc", ct.c_int64),
        ("floatMin", ct.c_double),
        ("floatMax", ct.c_double),
        ("floatInc", ct.c_double),
        ("representation", ct.c_uint8),
        ("displayNotation", ct.c_uint8),
        ("displayPrecision", ct.c_int64),
        ("strmaxLength", ct.c_int64),
        ("enumSelectedIndex", ct.c_int32),
        ("enumCount", ct.c_int64),
        ("pollingTime", ct.c_int64),
        ("unit", ct.c_char *512)  # Assuming SV_STRING_SIZE = 256
    ]


class SV_BUFFER_FLAG(ct.Structure):
    _fields_ = [
        ("value", ct.c_uint32),
        ("newData", ct.c_uint8),
        ("acquiring", ct.c_uint8),
        ("queued", ct.c_uint8),
        ("incomplete", ct.c_uint8)
    ]

class SV_IMAGE_FILE_TYPE(ct.c_int):
    PNG = 0
    BMP = 1
    RAW = 2

class SV_BUFFER_INFO(ct.Structure):
    _fields_ = [
        ("pImagePtr", ct.POINTER(ct.c_uint8)),  # Pointer to image data
        ("pUserPtr", ct.POINTER(ct.c_uint8)),   # User-defined pointer
        ("iSizeX", ct.c_size_t),               # Image width
        ("iSizeY", ct.c_size_t),               # Image height
        ("iImageSize", ct.c_size_t),           # Total image size in bytes
        ("flags", SV_BUFFER_FLAG),             # Buffer flags
        ("iPixelType", ct.c_uint64),           # Pixel format type
        ("iImageId", ct.c_uint64),             # Image ID
        ("iTimeStamp", ct.c_uint64),           # Timestamp
        ("iReserved2", ct.c_uint32),           # Reserved fields
        ("iReserved3", ct.c_uint32),
        ("iReserved4", ct.c_uint32),
        ("iReserved5", ct.c_uint32),
        ("iReserved6", ct.c_uint32)
    ]


class SVSCamera():
    """
    This is entirely chatgpt....
    Abstract class for controlling a camera.

    Subclasses implement minimal
    control over the following cameras:
     - Ximea (uses ximea python API `xiAPI <https://www.ximea.com/support/wiki/apis/Python>`_;
     - AVT   (uses `pymba <https://github.com/morefigs/pymba>`_,
       a python wrapper for AVT Vimba package).

    Examples
    --------
    Simple usage of a camera class::

        cam = AvtCamera()
        cam.open_camera()  # initialize the camera
        cam.set('exposure', 10)  # set exposure time in ms
        frame = cam.read()  # read frame
        cam.release()  # close the camera


    Attributes
    ----------
    cam :
        camera object (class depends on camera type).

    debug : bool
        if true, state of the camera is printed.


    """

    def __init__(self, downsampling=1, roi=(-1, -1, -1, -1),
                 serial_number = 'C0377030', interface_type=InterfaceType.CAMERA_LINK,
                 *args, **kwargs):
        """
        Parameters
        ----------
        debug : str
            if True, info about the camera state will be printed.
        """
        dll_path = "C://Program Files//SVS-VISTEK GmbH//SVCam Kit//SDK//bin//SVGenSDK64.dll"  # "..\\x64\\Release\\SVCaptureAPI.dll"

        self.interface_type = interface_type
        self.serial_number = serial_number
        self.sv_dll = ct.CDLL(dll_path)
        #super(Camera, self).__init__(*args, **kwargs)

    def get_feature_by_index(self, remote_device_handle, index):
        self.sv_dll.SVFeatureGetByIndex.argtypes = [ct.c_void_p, ct.c_uint32, ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVFeatureGetByIndex.restype = ct.c_int  # Assuming SV_RETURN is int
        feature_handle = ct.c_void_p()
        self.sv_dll.SVFeatureGetByIndex(remote_device_handle, ct.c_uint32(index), ct.byref(feature_handle))
        return feature_handle

    def get_feature_by_name(self, remote_device_handle, feature_name):
        self.sv_dll.SVFeatureGetByName.argtypes = [ct.c_void_p, ct.c_char_p, ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVFeatureGetByName.restype = ct.c_int  # Assuming SV_RETURN is int
        feature_name_bytes = ct.c_char_p(feature_name.encode())
        feature_handle = ct.c_void_p()
        result = self.sv_dll.SVFeatureGetByName(remote_device_handle, feature_name_bytes, ct.byref(feature_handle))
        if result == 0:  # Assuming 0 means success
            return feature_handle
        else:
            return None

    def get_feature_info(self, remote_device_handle, feature_handle):
        self.sv_dll.SVFeatureGetInfo.argtypes = [ct.c_void_p, ct.c_void_p, ct.POINTER(SV_FEATURE_INFO)]
        self.sv_dll.SVFeatureGetInfo.restype = ct.c_int  # Assuming SV_RETURN is int
        feature_info = SV_FEATURE_INFO()
        self.sv_dll.SVFeatureGetInfo(remote_device_handle, feature_handle, ct.byref(feature_info))
        return feature_info

    def get_feature_value_int64(self, remote_device_handle, feature_handle):
        self.sv_dll.SVFeatureGetValueInt64.argtypes = [ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_int64)]
        self.sv_dll.SVFeatureGetValueInt64.restype = ct.c_int  # Assuming SV_RETURN is int
        value = ct.c_int64()
        self.sv_dll.SVFeatureGetValueInt64(remote_device_handle, feature_handle, ct.byref(value))
        return value.value

    def set_feature_value_int64(self, remote_device_handle, feature_handle, value):
        self.sv_dll.SVFeatureSetValueInt64.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_int64]
        self.sv_dll.SVFeatureSetValueInt64.restype = ct.c_int  # Assuming SV_RETURN is int
        self.sv_dll.SVFeatureSetValueInt64(remote_device_handle, feature_handle, ct.c_int64(value))

    def get_feature_value_float(self, remote_device_handle, feature_handle):
        # Define function signature
        self.sv_dll.SVFeatureGetValueFloat.argtypes = [ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_double)]
        self.sv_dll.SVFeatureGetValueFloat.restype = ct.c_int  # Assuming SV_RETURN is int
        value = ct.c_double()
        self.sv_dll.SVFeatureGetValueFloat(remote_device_handle, feature_handle, ct.byref(value))
        return value.value

    def set_feature_value_float(self, remote_device_handle, feature_handle, value):
        self.sv_dll.SVFeatureSetValueFloat.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_double]
        self.sv_dll.SVFeatureSetValueFloat.restype = ct.c_int  # Assuming SV_RETURN is int
        self.sv_dll.SVFeatureSetValueFloat(remote_device_handle, feature_handle, ct.c_double(value))

    def allocate_stream_buffers(self, stream_handle, payload_size, buffer_count):
        self.sv_dll.SVStreamAnnounceBuffer.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_uint32, ct.c_void_p,
                                                       ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVStreamAnnounceBuffer.restype = ct.c_int
        self.sv_dll.SVStreamQueueBuffer.argtypes = [ct.c_void_p, ct.c_void_p]
        self.sv_dll.SVStreamQueueBuffer.restype = ct.c_int
        buffers = []
        buffer_handles = []
        for i in range(buffer_count):
            buffer = ct.create_string_buffer(payload_size)  # Equivalent to `new size_t[payloadSize]` in C++
            hBuffer = ct.c_void_p()
            result = self.sv_dll.SVStreamAnnounceBuffer(stream_handle, buffer, ct.c_uint32(payload_size), None,
                                                        ct.byref(hBuffer))
            if result != 0:  # Assuming non-zero means failure
                print(f"SVStreamAnnounceBuffer[{i}] Failed! Error Code: {result}")
                continue
            buffers.append(buffer)
            buffer_handles.append(hBuffer)
            queue_result = self.sv_dll.SVStreamQueueBuffer(stream_handle, hBuffer)
            if queue_result != 0:
                print(f"SVStreamQueueBuffer[{i}] Failed! Error Code: {queue_result}")
            else:
                print(f"Successfully allocated and queued {len(buffers)} buffers.")
        return buffers, buffer_handles  # Return allocated buffers and handles

    def flush_stream_queue(self, stream_handle, queneflag = SV_ACQ_QUEUE_TYPE.ALL_TO_INPUT):
        self.sv_dll.SVStreamFlushQueue.argtypes = [ct.c_void_p, ct.c_int]
        self.sv_dll.SVStreamFlushQueue.restype = ct.c_int  # Assuming SV_RETURN is int
        result = self.sv_dll.SVStreamFlushQueue(stream_handle, queneflag)
        if result == 0:
            print("Stream queue flushed successfully.")
        else:
            print(f"SVStreamFlushQueue failed with error code: {result}")

    def start_acquisition(self, stream_handle, acquire = 0xFFFFFFFFFFFFFFFF):  # INFINITE timeout
        self.sv_dll.SVStreamAcquisitionStart.argtypes = [ct.c_void_p, ct.c_int, ct.c_uint64]
        self.sv_dll.SVStreamAcquisitionStart.restype = ct.c_int  # Assuming SV_RETURN is int
        result = self.sv_dll.SVStreamAcquisitionStart(stream_handle, SV_ACQ_START_FLAGS.DEFAULT, ct.c_uint64(acquire))
        if result == 0:
            print("Stream acquisition started successfully.")
            return True
        else:
            print(f"SVStreamAcquisitionStart failed with error code: {result}")
            return False

    def stop_acquisition(self, stream_handle):
        self.sv_dll.SVStreamAcquisitionStop.argtypes = [ct.c_void_p, ct.c_int]
        self.sv_dll.SVStreamAcquisitionStart.restype = ct.c_int  # Assuming SV_RETURN is int
        result = self.sv_dll.SVStreamAcquisitionStop(stream_handle, SV_ACQ_STOP_FLAGS.DEFAULT)
        if result == 0:
            print("Stream acquisition stopped successfully.")
        else:
            print(f"SVStreamAcquisitionStop failed with error code: {result}")

    def execute_feature_command(self, remote_device_handle, feature_handle, timeout=5000):
        """ Executes a command feature (e.g., AcquisitionStart). """
        self.sv_dll.SVFeatureCommandExecute.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_uint32]
        self.sv_dll.SVFeatureCommandExecute.restype = ct.c_int  # Assuming SV_RETURN is int
        result = self.sv_dll.SVFeatureCommandExecute(remote_device_handle, feature_handle, ct.c_uint32(timeout))
        if result == 0:
            print("Feature command executed successfully!")
        else:
            print(f"ERROR: SVFeatureCommandExecute failed with error code: {result}")

    def SVUtilSaveImageToFile(self, info):
        """ Saves the image buffer to a file in the specified format. """

        # Ensure buffer pointer is valid
        if not info.pImagePtr or info.iImageSize == 0:
            print("ERROR: Invalid Image Pointer or Image Size is 0!")
        # Define function signature
        self.sv_dll.SVUtilSaveImageToFile.argtypes = [ct.POINTER(SV_BUFFER_INFO), ct.c_char_p, SV_IMAGE_FILE_TYPE]
        self.sv_dll.SVUtilSaveImageToFile.restype = ct.c_int  # Assuming SV_RETURN is int
        # Convert filename to ctypes-compatible format
        print(info.pImagePtr)
        file_name = "C://Users//Zichen//Desktop//moretrash//tttrash.png"
        file_name = file_name.encode("utf-8")
        file_name_bytes = bytes(memoryview(file_name))
        info_ref = ct.byref(info)
        print(f'new {info.pImagePtr}')
        self.sv_dll.SVUtilSaveImageToFile(info_ref, file_name_bytes, SV_IMAGE_FILE_TYPE(SV_IMAGE_FILE_TYPE.PNG))
        print(f'new {info.pImagePtr}')
        try:
            self.sv_dll.SVUtilSaveImageToFile(info_ref, file_name_bytes, SV_IMAGE_FILE_TYPE(SV_IMAGE_FILE_TYPE.PNG))
        except OSError:
            print(f'new {info.pImagePtr}')
        if result != 0:
            print(f"ERROR: SVUtilSaveImageToFile failed with error code: {result}")
        else:
            print(f"✅ Image successfully saved as {file_name}")

    def wait_for_new_buffer(self, stream_handle, timeout=1000):
        self.sv_dll.SVStreamWaitForNewBuffer.argtypes = [ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_void_p), ct.c_uint32]
        self.sv_dll.SVStreamWaitForNewBuffer.restype = ct.c_int  # Assuming SV_RETURN is int
        buffer_handle = ct.c_void_p()
        result = self.sv_dll.SVStreamWaitForNewBuffer(stream_handle, None, ct.byref(buffer_handle),ct.c_uint32(timeout))
        return buffer_handle, result

    def get_buffer_info(self, stream_handle, buffer_handle):
        self.sv_dll.SVStreamBufferGetInfo.argtypes = [ct.c_void_p, ct.c_void_p, ct.POINTER(SV_BUFFER_INFO)]
        self.sv_dll.SVStreamBufferGetInfo.restype = ct.c_int  # Assuming SV_RETURN is int
        buffer_info = SV_BUFFER_INFO()
        result = self.sv_dll.SVStreamBufferGetInfo(stream_handle, buffer_handle, ct.byref(buffer_info))
        return buffer_info, result

    def queue_buffer(self, stream_handle, buffer_handle):
        self.sv_dll.SVStreamQueueBuffer.argtypes = [ct.c_void_p, ct.c_void_p]
        self.sv_dll.SVStreamQueueBuffer.restype = ct.c_int  # Assuming SV_RETURN is int
        res = self.sv_dll.SVStreamQueueBuffer(stream_handle, buffer_handle)
        if res == 0:
            print('queued sucecessfully')

    def SVUtilBuffer12BitTo16Bit(self, buffer_info, pDest, pDestLength):
        """ Converts a 12-bit image buffer to 16-bit format. """
        # Ensure buffer pointer is valid
        if not buffer_info.pImagePtr or buffer_info.iImageSize == 0:
            print("ERROR: Invalid Source Image Pointer or Size!")
            return -1  # Return error code
        # Define function signature
        self.sv_dll.SVUtilBuffer12BitTo16Bit.argtypes = [SV_BUFFER_INFO, ct.POINTER(ct.c_ubyte), ct.c_int]
        self.sv_dll.SVUtilBuffer12BitTo16Bit.restype = ct.c_int  # Assuming SV_RETURN is int
        # Call the conversion function
        result = self.sv_dll.SVUtilBuffer12BitTo16Bit(buffer_info, pDest, pDestLength)
        if result != 0:
            print(f"ERROR: SVUtilBuffer12BitTo16Bit failed with error code: {result}")
        return pDest # Return the function result code

    def acquiring_imaging(self, stream_handle):
        """Main loop for continuously acquiring and processing images."""
        while self.acquiring:
            self.buffer_handle, result = self.wait_for_new_buffer(stream_handle, 1000000)
            if result == 0:  # New buffer received
                buffer_info, result = self.get_buffer_info(stream_handle, self.buffer_handle)
                if result != 0:  # Failed to retrieve buffer info
                    continue
                self.queue_buffer(stream_handle, self.buffer_handle)
                if buffer_info.pImagePtr:

                    print(buffer_info.pImagePtr, buffer_info.iSizeX, buffer_info.iSizeY)
                    imagedata = ct.cast(buffer_info.pImagePtr,
                                       ct.POINTER(ct.c_ubyte * buffer_info.iImageSize))
                    self.image = np.ndarray(buffer=imagedata.contents, dtype=np.uint8,
                                            shape=(buffer_info.iSizeY, buffer_info.iSizeX, 1))[:, :, 0]
                    print(self.image)
            elif result == CameraError.SV_ERROR_TIMEOUT:  # Timeout
                self.buffer_updated = False
                continue

    def list_all_features(self, remote_device_handle):
        """ Lists all available features and their values. """
        for i in range(100):  # Assume max 100 features
            # Get feature handle by index
            feature_handle = self.get_feature_by_index(remote_device_handle, i)
            if not feature_handle:
                print(f"No feature found at index {i}, stopping search.")
                break  # Stop if no more features exist
            # Get feature information
            feature_info = self.get_feature_info(remote_device_handle, feature_handle)
            if not feature_info:
                continue  # Skip if unable to get feature info
            feature_name = feature_info.name.decode(errors="ignore")
            print(f"Feature {i}: {feature_name}")
            # Try retrieving feature value (Int64)
            feature_value = self.get_feature_value_int64(remote_device_handle, feature_handle)
            if feature_value is not None:
                print(f"  → Value (Int64): {feature_value}")
            # Try retrieving feature value (Float)
            feature_value_float = self.get_feature_value_float(remote_device_handle, feature_handle)
            if feature_value_float is not None:
                print(f"  → Value (Float): {feature_value_float}")
            print("-" * 50)  # Separator for readability

    def revoke_all_buffers(self, ds_handle, ds_buf_count):
        self.sv_dll.SVStreamGetBufferId.argtypes = [ct.c_void_p, ct.c_uint32, ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVStreamGetBufferId.restype = ct.c_int
        self.sv_dll.SVStreamRevokeBuffer.argtypes = [ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_void_p), ct.c_void_p]
        self.sv_dll.SVStreamRevokeBuffer.restype = ct.c_int
        for i in range(ds_buf_count):
            hBuffer = ct.c_void_p()
            self.sv_dll.SVStreamGetBufferId(ds_handle, ct.c_uint32(i), ct.byref(hBuffer))
            if hBuffer.value:  # if hBuffer is not NULL
                pBuffer = ct.c_void_p()
                self.sv_dll.SVStreamRevokeBuffer(ds_handle, hBuffer, ct.byref(pBuffer), None)
                if pBuffer.value:
                    print(f"Buffer {i} revoked and memory pointer returned: {pBuffer.value}")
                    # If you did allocate with a custom new and need to free, you would need a corresponding free function.
                else:
                    print(f"Buffer {i} revoked, but no memory pointer returned.")
            else:
                print(f"Buffer {i}: No valid buffer handle returned.")

    def close_device(self, device_handle):
        self.sv_dll.SVDeviceClose.argtypes = [ct.c_void_p]
        self.sv_dll.SVDeviceClose.restype = ct.c_int
        ret = self.sv_dll.SVDeviceClose(device_handle)
        if ret != 0:
            print(f"SVDeviceClose failed with error code: {ret}")
        else:
            print("Device closed successfully.")

    def close_interface(self, interface_handle):
        self.sv_dll.SVInterfaceClose.argtypes = [ct.c_void_p]
        self.sv_dll.SVInterfaceClose.restype = ct.c_int
        ret = self.sv_dll.SVInterfaceClose(interface_handle)
        if ret != 0:
            print(f"SVInterfaceClose failed with error code: {ret}")
        else:
            print("Interface closed successfully.")

    def close_system(self, system_handle):
        self.sv_dll.SVSystemClose.argtypes = [ct.c_void_p]
        self.sv_dll.SVSystemClose.restype = ct.c_int
        ret = self.sv_dll.SVSystemClose(system_handle)
        if ret != 0:
            print(f"SVSystemClose failed with error code: {ret}")
        else:
            print("System closed successfully.")

    def close_lib(self):
        self.sv_dll.SVLibClose.argtypes = []
        self.sv_dll.SVLibClose.restype = ct.c_int
        ret = self.sv_dll.SVLibClose()
        if ret != 0:
            print(f"SVLibClose failed with error code: {ret}")
        else:
            print("Library closed successfully.")

    def open_camera(self, buffer_count = 10):
        self.buffer_count = buffer_count
        #initialize the lib
        self.sv_dll.SVLibInit.argtypes = [ct.c_char_p, ct.c_char_p, ct.c_char_p, ct.c_char_p]
        self.sv_dll.SVLibInit.restype = ct.c_int  # Assuming SV_RETURN is an integer type
        # Get environment variables (equivalent to GetEnvironmentVariableA in C++)
        tlipath = b"C://Program Files//Teledyne DALSA//Xtium2-CXP PX8//GenTL//cti//x64//CorXtium2CXPPX8GenTL.cti"#(os.environ.get("GENICAM_GENTL64_PATH", ""))
        genicam_root = os.environ.get("SVS_GENICAM_ROOT", "")
        genicam_cache = os.environ.get("SVS_GENICAM_CACHE", "")
        cl_protocol = os.environ.get("SVS_GENICAM_CLPROTOCOL", "")
        genicam_root = genicam_root.encode() if genicam_root else None
        genicam_cache = genicam_cache.encode() if genicam_cache else None
        cl_protocol = cl_protocol.encode() if cl_protocol else None
        self.sv_dll.SVLibInit(tlipath, genicam_root, genicam_cache, cl_protocol)

        #open system and get the system handle
        self.sv_dll.SVLibSystemOpen.argtypes = [ct.c_uint32, ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVLibSystemOpen.restype = ct.c_int  # Assuming SV_RETURN is int
        system_index = ct.c_uint32(0)
        self.system_handle = ct.c_void_p()
        self.sv_dll.SVLibSystemOpen(system_index, ct.byref(self.system_handle))

        #open the interface
        self.sv_dll.SVSystemUpdateInterfaceList.argtypes = [ct.c_void_p, ct.POINTER(ct.c_bool)]
        self.sv_dll.SVSystemUpdateInterfaceList.restype = ct.c_int  # Assuming SV_RETURN is int
        list_changed = ct.c_bool()
        self.sv_dll.SVSystemUpdateInterfaceList(self.system_handle, ct.byref(list_changed))
        # get id
        self.sv_dll.SVSystemGetInterfaceId.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_char_p, ct.POINTER(ct.c_size_t)]
        self.sv_dll.SVSystemGetInterfaceId.restype = ct.c_int  # Assuming SV_RETURN is int
        interface_index = ct.c_uint32(0)
        buffer_size = ct.c_size_t(128)  # Adjust size if needed
        self.interface_id = ct.create_string_buffer(128)
        self.sv_dll.SVSystemGetInterfaceId(self.system_handle, interface_index, self.interface_id, ct.byref(buffer_size))
        #actually get interface
        self.sv_dll.SVSystemInterfaceOpen.argtypes = [ct.c_void_p, ct.c_char_p, ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVSystemInterfaceOpen.restype = ct.c_int  # Assuming SV_RETURN is int
        self.interface_handle = ct.c_void_p()
        interface_id_bytes = ct.c_char_p(self.interface_id.value)
        self.sv_dll.SVSystemInterfaceOpen(self.system_handle, interface_id_bytes, ct.byref(self.interface_handle))

        #finally, lets open up the god damn camera
        #refresh list
        self.sv_dll.SVInterfaceUpdateDeviceList.argtypes = [ct.c_void_p, ct.POINTER(ct.c_bool)]
        self.sv_dll.SVInterfaceUpdateDeviceList.restype = ct.c_int  # Assuming SV_RETURN is int
        list_changed = ct.c_bool()
        self.sv_dll.SVInterfaceUpdateDeviceList(self.interface_handle, ct.byref(list_changed))
        #get the device id
        self.sv_dll.SVInterfaceGetDeviceId.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_char_p, ct.POINTER(ct.c_size_t)]
        self.sv_dll.SVInterfaceGetDeviceId.restype = ct.c_int  # Assuming SV_RETURN is int
        buffer_size = ct.c_size_t(128)  # Adjust size if needed
        self.device_id = ct.create_string_buffer(128)  # Stores char*
        device_index = ct.c_uint32(0)
        self.sv_dll.SVInterfaceGetDeviceId(self.interface_handle, device_index, self.device_id, ct.byref(buffer_size))
        #get the device to open
        self.sv_dll.SVInterfaceDeviceOpen.argtypes = [ct.c_void_p, ct.c_char_p, ct.c_int, ct.POINTER(ct.c_void_p), ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVInterfaceDeviceOpen.restype = ct.c_int  # Assuming SV_RETURN is int
        device_id_bytes = ct.c_char_p(self.device_id.value)
        self.device_handle = ct.c_void_p()
        self.remote_device_handle = ct.c_void_p()
        self.sv_dll.SVInterfaceDeviceOpen(self.interface_handle, device_id_bytes,  SV_DEVICE_ACCESS_FLAGS.CONTROL, ct.byref(self.device_handle),
        ct.byref(self.remote_device_handle))

        # start streaming
        #get stream id
        self.sv_dll.SVDeviceGetStreamId.argtypes = [ct.c_void_p, ct.c_uint32, ct.c_char_p, ct.POINTER(ct.c_size_t)]
        self.sv_dll.SVDeviceGetStreamId.restype = ct.c_int  # Assuming SV_RETURN is int
        stream_index = ct.c_uint32(0)
        buffer_size = ct.c_size_t(128)  # Adjust size if needed
        self.stream_id = ct.create_string_buffer(128)  # Stores char*
        self.sv_dll.SVDeviceGetStreamId(self.device_handle, stream_index, self.stream_id, ct.byref(buffer_size))
        #open streamming
        self.sv_dll.SVDeviceStreamOpen.argtypes = [ct.c_void_p, ct.c_char_p, ct.POINTER(ct.c_void_p)]
        self.sv_dll.SVDeviceStreamOpen.restype = ct.c_int  # Assuming SV_RETURN is int
        stream_id_bytes = ct.c_char_p(self.stream_id.value)
        self.stream_handle = ct.c_void_p()
        self.sv_dll.SVDeviceStreamOpen(self.device_handle, stream_id_bytes, ct.byref(self.stream_handle))

        #start acquisition
        feature_handle = self.get_feature_by_name(self.remote_device_handle, 'TLParamsLocked')
        self.set_feature_value_int64(self.remote_device_handle, feature_handle, 1)
        feature_handle = self.get_feature_by_name(self.remote_device_handle, 'PayloadSize')
        self.payloadsize = self.get_feature_value_int64(self.remote_device_handle, feature_handle)
        self.buffers, self.buffer_handles = self.allocate_stream_buffers(self.stream_handle, self.payloadsize, buffer_count=self.buffer_count)
        self.flush_stream_queue(self.stream_handle)
        self.start_acquisition(self.stream_handle)
        feature_handle = self.get_feature_by_name(self.remote_device_handle, 'AcquisitionStart')
        self.execute_feature_command(self.remote_device_handle, feature_handle)

        self.last_buffer_info = None
        self.buffer_updated = False
        self.acquiring = True
        self.acquiring_thread = threading.Thread(target=self.acquiring_imaging, args=(self.stream_handle,), daemon=True)
        self.acquiring_thread.start()


        return('done')

    def set(self, param, val):
        """Set exposure time or the framerate to the camera.

        Parameters
        ----------
        param : str
            parameter key ('exposure', 'framerate'));
        val :
            value to be set (exposure time in ms, or framerate in Hz);

        """
        if param == 'exposure':
            feature_handle = self.get_feature_by_name(self.remote_device_handle, 'Exposure')
            self.set_feature_value_float(self.remote_device_handle, feature_handle, val)
        elif param == 'framerate':
            feature_handle = self.get_feature_by_name(self.remote_device_handle, 'AcquisitionFrameRate')
            self.set_feature_value_float(self.remote_device_handle, feature_handle, val)
        elif param =='gain':
            feature_handle = self.get_feature_by_name(self.remote_device_handle, 'Gain')
            self.set_feature_value_float(self.remote_device_handle, feature_handle, val)

    def read(self):
        """Grab frame from the camera and returns it as an NxM numpy array.

        Returns
        -------
        np.array
                the grabbed frame, or None if an error occurred.

        """
        if self.last_buffer_info is not None:
            pixeltype = self.last_buffer_info.iPixelType
            bpp = (pixeltype & 0xff0000) >> 16
            if (bpp == 8):
                # imagedata = ct.cast(self.last_buffer_info.pImagePtr,
                #                     ct.POINTER(ct.c_ubyte * self.last_buffer_info.iImageSize))
                # self.image = np.ndarray(buffer=imagedata.contents, dtype=np.uint8,
                #                         shape=(self.last_buffer_info.iSizeY, self.last_buffer_info.iSizeX, 1))[:, :, 0].copy()
                self.SVUtilSaveImageToFile(self.last_buffer_info, "C://Users//Zichen//Desktop//moretrash//tttrash.png", SV_IMAGE_FILE_TYPE.PNG)
            elif (bpp == 12):
                self.image = np.ndarray(dtype=np.uint16,
                                        shape=(self.last_buffer_info.iSizeY, self.last_buffer_info.iSizeX, 1))
                self.SVUtilBuffer12BitTo16Bit(self.last_buffer_info, self.image.ct.data_as(ct.c_void_p),
                                              self.last_buffer_info.iSizeY * self.last_buffer_info.iSizeX * 2)
        else:
            self.image = np.full([10, 10], 255, dtype=np.uint8)
        return self.image

    def save(self):
        print(self.last_buffer_info)

        if self.last_buffer_info is not None:
            pixeltype = self.last_buffer_info.iPixelType
            bpp = (pixeltype & 0xff0000) >> 16
            if (bpp == 8):
                # imagedata = ct.cast(self.last_buffer_info.pImagePtr,
                #                     ct.POINTER(ct.c_ubyte * self.last_buffer_info.iImageSize))
                # self.image = np.ndarray(buffer=imagedata.contents, dtype=np.uint8,
                #                         shape=(self.last_buffer_info.iSizeY, self.last_buffer_info.iSizeX, 1))[:, :, 0].copy()
                self.SVUtilSaveImageToFile(self.last_buffer_info, "C://Users//Zichen//Desktop//moretrash//tttrash.png",
                                           SV_IMAGE_FILE_TYPE.PNG)
            elif (bpp == 12):
                self.image = np.ndarray(dtype=np.uint16,
                                        shape=(self.last_buffer_info.iSizeY, self.last_buffer_info.iSizeX, 1))
                self.SVUtilBuffer12BitTo16Bit(self.last_buffer_info, self.image.ct.data_as(ct.c_void_p),
                                              self.last_buffer_info.iSizeY * self.last_buffer_info.iSizeX * 2)
        else:
            self.image = np.full([10, 10], 255, dtype=np.uint8)

    def release(self):
        """Close the camera.
        """
        print('releasing')
        self.acquiring = False
        # if self.acquiring_thread.is_alive():
        #     self.acquiring_thread.join()
        #     print('thread stopping')

        feature_handle = self.get_feature_by_name(self.remote_device_handle, 'AcquisitionStop')
        self.execute_feature_command(self.remote_device_handle, feature_handle)
        self.stop_acquisition(self.stream_handle)
        self.flush_stream_queue(self.stream_handle, SV_ACQ_QUEUE_TYPE.INPUT_TO_OUTPUT)
        self.flush_stream_queue(self.stream_handle, SV_ACQ_QUEUE_TYPE.OUTPUT_DISCARD)
        self.revoke_all_buffers(self.stream_handle, self.buffer_count)
        feature_handle = self.get_feature_by_name(self.remote_device_handle, 'TLParamsLocked')
        self.set_feature_value_int64(self.remote_device_handle, feature_handle, 0)
        self.close_device(self.device_handle)
        self.close_interface(self.interface_handle)
        self.close_system(self.system_handle)
        self.close_lib()

svs_Camera = SVSCamera()
svs_Camera.open_camera()
time.sleep(5)
# # for i in range(100):
# #     svs_Camera.save()
#
svs_Camera.release()
