import sys
import os
import glob
import time
import random
import datetime
import serial
from typing import NamedTuple
import keyboard
from pypylon import pylon, genicam
import cv2


class TitaniaTestParams(NamedTuple):
    left_serial: str
    right_serial: str
    output_folderpath: str
    capture_fps: float
    save_fps: float
    save_images: bool
    capture_temperature: bool
    enable_external_serial: bool
    external_serial_port: str
    virtual_camera: bool
    timeout: float
    right_exposure: float
    left_exposure: float


def getLeftRightSerialFromTitaniaSerial(titania_serial: str) -> str:
    # Get left and right camera serials from the given titania serial
    # the titania serial should exists in the cameras user defined name
    # in the following format:
    # 'I3DRTitania-XXXXXXXX_l' and 'I3DRTitania-XXXXXXXX_r'
    try:
        # Get the transport layer factory.
        tlFactory = pylon.TlFactory.GetInstance()

        # Get all attached devices and exit application if no device is found.
        devices = tlFactory.EnumerateDevices()
        if len(devices) < 2:
            raise pylon.RuntimeException(
                "Missing cameras. Requires at least 2 cameras are connected.")

        # Create an array of instant cameras
        left_serial = None
        right_serial = None

        # Create and attach Pylon Devices.
        for device in devices:
            # Get camera serials from user defined name
            camera_defined_id = device.GetUserDefinedName()
            if "I3DRTitania" in camera_defined_id:
                camera_defined_id_array = camera_defined_id.split("_")
                if len(camera_defined_id_array) != 3:
                    err_msg = "Invalid device user id name format: " \
                        + camera_defined_id + " Expected the format: \
                        'I3DRTitania-XXXXXXXX_l'"
                    raise Exception(err_msg)
                cam_titania_serial = camera_defined_id_array[1]
                if cam_titania_serial == titania_serial:
                    if "l" in camera_defined_id:
                        left_serial = device.GetSerialNumber()
                    elif "r" in camera_defined_id:
                        right_serial = device.GetSerialNumber()

        if left_serial is None or right_serial is None:
            error_msg = "Failed to find valid camera serials \
                on connected devices."
            raise Exception(error_msg)

        return left_serial, right_serial

    except genicam.GenericException as e:
        # Error handling
        print("An exception occurred when getting camera serials.", e)
        return {}


def validateTitaniaTestParams(test_params: TitaniaTestParams) -> bool:
    # Check valid camera serial
    if test_params.left_serial == "" and test_params.right_serial == "":
        raise Exception("Camera serial empty")
    # Save rate must be less than or equal to capture rate
    if test_params.save_fps > test_params.capture_fps:
        raise Exception("Save FPS must be less than or equal to capture FPS")


def enableCameraEmulation(enable: bool):
    if enable:
        os.environ["PYLON_CAMEMU"] = "2"
    else:
        os.environ["PYLON_CAMEMU"] = "0"


def checkSerialPairConnected(left_serial: str, right_serial: str) -> bool:
    camera_serials = getCameraSerials()
    # Check they are connected
    if left_serial not in camera_serials:
        raise Exception("Left camera not found: " + left_serial)
    if right_serial not in camera_serials:
        raise Exception("Right camera not found: " + right_serial)
    return True


def getSerialPairConnected() -> list:
    camera_serials = getCameraSerials()
    # Check only two cameras are connected and get their serials
    if len(camera_serials) > 2:
        raise Exception("Too many camera connected. \
            Please specify --left_serial and --right_serial.")
    if len(camera_serials) < 2:
        raise Exception("Not enough camera connected. Found " +
                        str(len(camera_serials)) + " cameras.")
    left_serial = camera_serials[0]
    right_serial = camera_serials[1]

    return left_serial, right_serial


def listAvailableSerialDevices() -> list:
    """ Lists serial port names
        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        # only look for COM port 2 +
        ports = ['COM%s' % (i + 2) for i in range(256)]
    elif sys.platform.startswith('linux'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


def getFirstSerialDevice() -> str:
    device_list = listAvailableSerialDevices()
    if len(device_list) <= 0:
        return None
    return device_list[0]


def getCameraSerials() -> list:
    # Get camera serials of currently connected basler devices
    serial_list = []
    try:
        # Get the transport layer factory.
        tlFactory = pylon.TlFactory.GetInstance()

        # Get all attached devices and exit application if no device is found.
        devices = tlFactory.EnumerateDevices()
        if len(devices) == 0:
            return []

        # Create and attach all Pylon Devices.
        for device in devices:

            # Print the serial of the camera.
            cam_serial = device.GetSerialNumber()
            serial_list.append(cam_serial)

        return serial_list

    except genicam.GenericException as e:
        # Error handling
        print("An exception occurred when getting camera serials.", e)
        return []


def getLogFileName(timestamp: str) -> str:
    # Create file name from unix time
    log_file_name = "TitaniaTest_" + timestamp + ".txt"
    return log_file_name


def saveFrame(excel_time, left_image_filename, right_image_filename,
              left_temp, right_temp, test_params, external_serial_data,
              left_success, right_success, external_serial_success,
              log_filepath, hour_log_filepath, day_log_filepath) -> None:
    # create log message
    log_msg = excel_time+","
    if test_params.save_images:
        log_msg += left_image_filename + "," + right_image_filename + ","
    if test_params.capture_temperature:
        log_msg += left_temp + "," + right_temp + ","
    if test_params.enable_external_serial:
        log_msg += external_serial_data + ","
    log_msg += left_success + "," + right_success
    if test_params.enable_external_serial:
        log_msg += "," + external_serial_success
    log_msg += "\n"
    print(log_msg)

    log_files = [log_filepath, hour_log_filepath, day_log_filepath]
    for log_file in log_files:
        # Append log message line to file
        f = open(log_file, "a")
        f.write(log_msg)
        f.close()


def connectCameras(test_params):
    try:
        # Get the transport layer factory.
        tlFactory = pylon.TlFactory.GetInstance()

        # Get all attached devices and exit application if no device is found.
        devices = tlFactory.EnumerateDevices()
        if len(devices) < 2:
            raise pylon.RuntimeException(
                "Missing cameras. Requires at least 2 cameras are connected.")

        # Create an array of instant cameras
        cameras = pylon.InstantCameraArray(2)
        cameras_found = [False, False]

        # Create and attach Pylon Devices.
        # Attach to camera serials from params
        # Left camera assigned to index 0, right camera to index 1
        for device in devices:
            # Print the serial of the camera.
            cam_serial = device.GetSerialNumber()
            if (cam_serial == test_params.left_serial):
                cameras[0].Attach(tlFactory.CreateDevice(device))
                cameras_found[0] = True
            if (cam_serial == test_params.right_serial):
                cameras[1].Attach(tlFactory.CreateDevice(device))
                cameras_found[1] = True

        if False in cameras_found:
            error_msg = "Failed to find specified camera serials \
                on connected devices."
            raise Exception(error_msg)

        # Start capture
        cameras.StartGrabbing(
            pylon.GrabStrategy_LatestImageOnly)

        for cam in cameras:
            # Set capture rate
            if test_params.virtual_camera:
                cam.AcquisitionFrameRateAbs.SetValue(test_params.capture_fps)
            else:
                cam.AcquisitionFrameRate.SetValue(test_params.capture_fps)
            cam.AcquisitionFrameRateEnable.SetValue(True)

        # Set exposure
        cameras[0].ExposureTime.SetValue(test_params.left_exposure)
        cameras[1].ExposureTime.SetValue(test_params.right_exposure)

        # Flip left camera images
        if not test_params.virtual_camera:
            cameras[0].ReverseX.SetValue(True)
            cameras[0].ReverseY.SetValue(True)

    except genicam.GenericException as e:
        # Error handling
        print("Camera exception occurred during test setup: ", e)
        exit(1)

    return cameras


def write_log_header(log_filepath, test_params):
    # create log file header line
    header_msg = "time,"
    if test_params.save_images:
        header_msg += "left_img,right_img,"
    if test_params.capture_temperature:
        header_msg += "left_temp,right_temp,"
    if test_params.enable_external_serial:
        header_msg += "external_data,"
    header_msg += "left_success,right_success"
    if test_params.enable_external_serial:
        header_msg += ",external_success"
    header_msg += "\n"
    # write to file
    f = open(log_filepath, "w")
    f.write(header_msg)
    f.close()


def string_cleaning(str_to_clean):
    return str_to_clean.replace('\n', ' ').replace('\r', '').replace(',', '.')


def run(test_params: TitaniaTestParams) -> int:

    exit_code = 0
    test_start_time = datetime.datetime.now()
    timestamp = test_start_time.strftime('%Y-%m-%d_%H_%M_%S_%f')
    # Generate names for filepaths
    log_filename = getLogFileName(timestamp)
    # create folder if it does not exist
    if not os.path.exists(test_params.output_folderpath):
        os.makedirs(test_params.output_folderpath)
    log_filepath = os.path.join(test_params.output_folderpath, log_filename)

    print("Test started: ", timestamp)

    if (test_params.enable_external_serial):
        # connect to external serial device
        ext_ser = serial.Serial(test_params.external_serial_port)
        ext_ser.flushInput()

    cameras = connectCameras(test_params)

    # Write log file header line
    write_log_header(log_filepath, test_params)

    # Calculate save rate (in seconds)
    save_rate = 1.0 / test_params.save_fps
    last_save_time = time.time()

    cam_err_msg = "CAMERA ERROR. likely camera disconnected: "
    cam_run_err_msg = \
        "CAMERA RUNTIME ERROR. likely camera disconnected: "

    try:
        start_time = time.time()
        while True:
            try:
                if test_params.timeout > 0:
                    test_duration = time.time() - start_time
                    if test_duration > test_params.timeout:
                        exit_code = 0
                        break

                # Get capture time
                time_now = datetime.datetime.now()
                # Convert to excel datetime serial
                excel_time = time_now.strftime('%Y-%m-%d %H:%M:%S.%f')
                image_tag_time = time_now.strftime('%Y-%m-%d_%H_%M_%S_%f')

                # Create new folder for data on every day
                day_timestamp = time_now.strftime('%Y-%m-%d')
                day_folder_path = os.path.join(
                    test_params.output_folderpath, day_timestamp)
                day_log_filepath = os.path.join(
                    day_folder_path, getLogFileName(day_timestamp))
                if not os.path.exists(day_folder_path):
                    os.makedirs(day_folder_path)
                    write_log_header(day_log_filepath, test_params)

                # Create new folder for data on every hour
                day_hour_timestamp = time_now.strftime('%Y-%m-%d %H')
                hour_folder_path = os.path.join(
                    day_folder_path, day_hour_timestamp)
                hour_log_filepath = os.path.join(
                    hour_folder_path, getLogFileName(day_hour_timestamp))
                if not os.path.exists(hour_folder_path):
                    os.makedirs(hour_folder_path)
                    write_log_header(hour_log_filepath, test_params)

                # Define default values for log data
                left_temp = ""
                right_temp = ""
                ext_ser_data = ""
                left_image_filename = ""
                right_image_filename = ""
                left_success = "0"
                right_success = "0"
                ext_ser_success = "0"

                reconnect_camera = False

                save_this_frame = False

                if test_params.enable_external_serial:
                    try:
                        ext_ser.flushInput()
                        ser_bytes = ext_ser.readline()
                        # read twice to make sure complete data is received
                        ser_bytes = ext_ser.readline()
                        ext_ser_data = ser_bytes.decode("utf-8").rstrip()
                        ext_ser_success = "1"
                    except serial.SerialException as e:
                        # There is no new data from serial port
                        ext_ser_data = ""
                        ext_ser_success = \
                            "SERAIL FAILED. Likely disconnected: {}".format(
                                str(e))
                        try:
                            # try to re-connect
                            ext_ser.close()
                            ext_ser = serial.Serial(
                                test_params.external_serial_port)
                            ext_ser.flushInput()
                        except serial.SerialException:
                            pass
                        except TypeError:
                            pass
                    except TypeError:
                        # Disconnect of USB->UART occured
                        ext_ser_data = ""
                        ext_ser_success = "DISCONNECTED"
                        try:
                            # try to re-connect
                            ext_ser.close()
                            ext_ser = serial.Serial(
                                test_params.external_serial_port)
                            ext_ser.flushInput()
                        except serial.SerialException:
                            pass
                        except TypeError:
                            pass
                    if ext_ser_data != "":
                        # clean external serial data for
                        # use in comma separated log file
                        ext_ser_data = str(ext_ser_data)

                try:
                    grabbing = cameras.IsGrabbing()
                except genicam.GenericException as e:
                    left_success = cam_err_msg + "{}".format(str(e))
                    right_success = cam_err_msg + "{}".format(str(e))
                    grabbing = False
                    reconnect_camera = True
                except genicam.RuntimeException as e:
                    left_success = cam_run_err_msg + "{}".format(str(e))
                    right_success = cam_run_err_msg + "{}".format(str(e))
                    grabbing = False
                    reconnect_camera = True
                except pylon.RuntimeException as e:
                    left_success = cam_run_err_msg + "{}".format(str(e))
                    right_success = cam_run_err_msg + "{}".format(str(e))
                    grabbing = False
                    reconnect_camera = True

                # Check cameras are grabbing
                if grabbing:
                    grabResult_left = None
                    grabResult_right = None
                    # Read camera data
                    try:
                        grabResult_left = cameras[0].RetrieveResult(
                            20000, pylon.TimeoutHandling_ThrowException)
                    except pylon.TimeoutException as e:
                        left_success = "CAMERA TIMEOUT: {}".format(str(e))
                    except genicam.GenericException as e:
                        left_success = cam_err_msg + "{}".format(str(e))
                        reconnect_camera = True
                    except genicam.RuntimeException as e:
                        left_success = cam_run_err_msg + "{}".format(str(e))
                        reconnect_camera = True
                    except pylon.RuntimeException as e:
                        left_success = cam_run_err_msg + "{}".format(str(e))
                        reconnect_camera = True

                    try:
                        grabResult_right = cameras[1].RetrieveResult(
                            20000, pylon.TimeoutHandling_ThrowException)
                    except pylon.TimeoutException as e:
                        right_success = "CAMERA TIMEOUT: {}".format(str(e))
                    except genicam.GenericException as e:
                        right_success = cam_err_msg + "{}".format(str(e))
                        reconnect_camera = True
                    except genicam.RuntimeException as e:
                        right_success = cam_run_err_msg + "{}".format(str(e))
                        reconnect_camera = True
                    except pylon.RuntimeException as e:
                        right_success = cam_run_err_msg + "{}".format(str(e))
                        reconnect_camera = True

                    time_since_save = time.time() - last_save_time
                    if time_since_save > save_rate:
                        save_this_frame = True
                        last_save_time = time.time()

                    if save_this_frame:
                        # Save camera images to file
                        try:
                            if grabResult_left is not None:
                                if grabResult_left.GrabSucceeded():
                                    left_success = "1"
                                    if test_params.save_images:
                                        img = grabResult_left.GetArray()
                                        left_image_filename = \
                                            image_tag_time + "_l.png"
                                        left_image_filepath = os.path.join(
                                            hour_folder_path,
                                            left_image_filename)
                                        cv2.imwrite(left_image_filepath, img)
                                else:
                                    left_success = "GRAB FAIL"
                            else:
                                left_success = "NO IMAGE DATA"
                        except genicam.GenericException as e:
                            left_success = cam_err_msg + "{}".format(str(e))
                            reconnect_camera = True
                        except genicam.RuntimeException as e:
                            left_success = \
                                cam_run_err_msg + "{}".format(str(e))
                            reconnect_camera = True
                        except pylon.RuntimeException as e:
                            left_success = \
                                cam_run_err_msg + "{}".format(str(e))
                            reconnect_camera = True

                        try:
                            if grabResult_right is not None:
                                if grabResult_right.GrabSucceeded():
                                    right_success = "1"
                                    if test_params.save_images:
                                        img = grabResult_right.GetArray()
                                        right_image_filename = \
                                            image_tag_time + "_r.png"
                                        right_image_filepath = os.path.join(
                                            hour_folder_path,
                                            right_image_filename)
                                        cv2.imwrite(right_image_filepath, img)
                                else:
                                    right_success = "GRAB FAIL"
                            else:
                                right_success = "NO IMAGE DATA"
                        except genicam.GenericException as e:
                            right_success = cam_err_msg + "{}".format(str(e))
                            reconnect_camera = True
                        except genicam.RuntimeException as e:
                            right_success = \
                                cam_run_err_msg + "{}".format(str(e))
                            reconnect_camera = True
                        except pylon.RuntimeException as e:
                            right_success = \
                                cam_run_err_msg + "{}".format(str(e))
                            reconnect_camera = True

                        if test_params.capture_temperature:
                            # Get temperature
                            if test_params.virtual_camera:
                                # generate fake temperature values
                                left_temp_data = random.uniform(30, 60)
                                right_temp_data = random.uniform(30, 60)
                            else:
                                try:
                                    # read temperature from cameras
                                    left_temp_data = \
                                        cameras[0].DeviceTemperature.GetValue()
                                    right_temp_data = \
                                        cameras[1].DeviceTemperature.GetValue()
                                except genicam.GenericException as e:
                                    left_success = \
                                        cam_err_msg + "{}".format(str(e))
                                    right_success = \
                                        cam_err_msg + "{}".format(str(e))
                                    reconnect_camera = True
                                except genicam.RuntimeException as e:
                                    left_success = \
                                        cam_run_err_msg + "{}".format(str(e))
                                    right_success = \
                                        cam_run_err_msg + "{}".format(str(e))
                                    reconnect_camera = True
                                except pylon.RuntimeException as e:
                                    left_success = \
                                        cam_run_err_msg + "{}".format(str(e))
                                    right_success = \
                                        cam_run_err_msg + "{}".format(str(e))
                                    reconnect_camera = True
                            left_temp = "{:.3F}".format(left_temp_data)
                            right_temp = "{:.3F}".format(right_temp_data)
                else:
                    left_success = "NOT GRABBING"
                    right_success = "NOT GRABBING"
                    reconnect_camera = True

                if save_this_frame:
                    left_success = string_cleaning(left_success)
                    right_success = string_cleaning(right_success)
                    ext_ser_data = string_cleaning(ext_ser_data)
                    ext_ser_success = string_cleaning(ext_ser_success)

                    saveFrame(
                        excel_time, left_image_filename, right_image_filename,
                        left_temp, right_temp, test_params, ext_ser_data,
                        left_success, right_success, ext_ser_success,
                        log_filepath, hour_log_filepath, day_log_filepath)

                if reconnect_camera:
                    grab_except_msg = \
                        "Unexpected exception when trying to re-start grabbing"
                    # try to restart camera connection
                    try:
                        cameras = connectCameras(test_params)
                    except pylon.RuntimeException as e:
                        print(str(e))
                    except:
                        print(grab_except_msg + ": ", sys.exc_info()[0])

                if keyboard.is_pressed("q"):
                    print("Test manually stopped")
                    exit_code = 1
                    break

            except genicam.GenericException:
                saveFrame(excel_time, left_image_filename, right_image_filename,
                          left_temp, right_temp, test_params, ext_ser_data,
                          left_success, right_success, ext_ser_success,
                          log_filepath)
    except KeyboardInterrupt:
        print("Test manually stopped.")
        exit_code = 0
        return exit_code
    except:
        print("Unexpected exception during test:", sys.exc_info()[0])
        exit_code = 1
        return exit_code

    return exit_code


# Entry point used to debug Titania Test
def main() -> int:
    # Choose params
    virtual_cams = True
    left_serial = ""
    right_serial = ""
    output_folderpath = "."
    capture_fps = 10.0
    save_fps = 10.0
    timeout = 0.0  # zero = no timeout
    save_images = True
    capture_temp = True
    enable_external_serial = True
    exposure = 110000.0  # us

    enableCameraEmulation(virtual_cams)
    # Check connected devices against arguments
    if left_serial != "":
        # If serials are specified then check they are connected
        checkSerialPairConnected(left_serial, right_serial)
    if left_serial == "":
        # If serials are not specifed then
        # check only two cameras are connected and get their serials
        left_serial, right_serial = getSerialPairConnected()
    if left_serial is None or right_serial is None:
        # This shouldn't be possible as previous error checking
        # should always set serials or raise an exception
        raise Exception("Failed to get valid camera serials")
    external_serial_port = None
    if enable_external_serial:
        # Check if external serial device is avaiable
        external_serial_port = getFirstSerialDevice()
        if external_serial_port is None:
            raise Exception("Failed to find serial device for external data")
    # Define test parameters
    test_params = TitaniaTestParams(
        left_serial=left_serial, right_serial=right_serial,
        output_folderpath=output_folderpath,
        capture_fps=capture_fps,
        save_fps=save_fps,
        save_images=save_images,
        capture_temperature=capture_temp,
        enable_external_serial=enable_external_serial,
        external_serial_port=external_serial_port,
        virtual_camera=virtual_cams,
        timeout=timeout,
        left_exposure=exposure,
        right_exposure=exposure
    )
    validateTitaniaTestParams(test_params)
    # Run test
    exit_code = run(test_params)
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
