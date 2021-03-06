import argparse
import sys
import os
import TitaniaTest


def parse_args() -> argparse.Namespace:
    # parse command line argument
    parser = argparse.ArgumentParser(description="Titania Testing")
    parser.add_argument('--output', type=str, default=".", help="\
        Folderpath to store test results. \n \
        Test data includes log file of results and \
        any images captured during the test.")
    parser.add_argument('--capture_fps', type=float, default=1.0, help="\
        Data capture rate (frames per second). All data is captured in sync.")
    parser.add_argument('--save_fps', type=float, default=1.0, help="\
        Data save rate (frames per second). \
        MUST be less than or equal to capture_fps.")
    parser.add_argument('--disable_temp', action='store_true', help="\
        Disable capturing of temperature data \
        from cameras during test.")
    parser.add_argument('--disable_images', action='store_true', help="\
        Disable saving of images during. \
        Image will still be grabbed from camera but \
        will not be saved to file.")
    parser.add_argument('--enable_external_serial', action='store_true', help="\
        Enable external serial comms.")
    parser.add_argument('--external_serial_port', type=str, default="", help="\
        Serial port for external device. \
        If not specified will use first device found. \
        Requires 'enable_external_serial' to be set.")
    parser.add_argument('--left_serial', type=str, default="", help="\
        Camera serial number for left camera. \
        If not specified will connect to first two \
        basler cameras found connected.")
    parser.add_argument('--right_serial', type=str, default="", help="\
        Camera serial number for right camera. \
        If not specified will connect to first two \
        basler cameras found connected.")
    parser.add_argument('--titania_serial', type=str, default="", help="\
        Titania unique serial number. \
        Found printed on the back of Titania.")
    parser.add_argument('--virtual', action='store_true', help="\
        Enable camera emulation. Useful for testing. \
        Cameras are expected with serials '0815-0000' & '0815-0001'")
    parser.add_argument('--timeout', type=float, default=0.0, help="\
        Maximum time to run test (seconds).")
    parser.add_argument('--left_exposure', type=float, default=110000.0, help="\
        Left camera exposure (us)")
    parser.add_argument('--right_exposure', type=float, default=110000.0, help="\
        Right camera exposure (us)")
    args = parser.parse_args()
    # Check arguments are valid
    # If one camera serial is given then both must be given
    left_serial_given = args.left_serial != ""
    right_serial_given = args.right_serial != ""
    titania_serial_given = args.titania_serial != ""
    external_serial_given = args.external_serial_port != ""
    if left_serial_given and not right_serial_given:
        err_msg = "left_serial given without right_serial. \
            Both left and right MUST be given if specifing camera serials."
        raise Exception(err_msg)
    if right_serial_given and not left_serial_given:
        err_msg = "right_serial given without left_serial. \
            Both left and right MUST be given if specifing camera serials."
        raise Exception(err_msg)
    if titania_serial_given and (left_serial_given or right_serial_given):
        err_msg = "Cannot specify titania_serial \
            and left_serial or right_serial. If you have titania serial \
            left_serial and right_serial are no longer requred."
        raise Exception(err_msg)
    if external_serial_given and not args.enable_external_serial:
        err_msg = "External serial provided but external serial is not enabled. \
            add '--enable_external_serial' to enable external serial."
        raise Exception(err_msg)
    if args.timeout < 0.0:
        raise Exception("Timeout must be positive number in seconds.")
    # Save rate must be less than or equal to capture rate
    if args.save_fps > args.capture_fps:
        raise Exception("Save FPS must be less than or equal to capture FPS")
    return args


def main() -> int:
    # Get command line arguments
    args = parse_args()
    TitaniaTest.enableCameraEmulation(args.virtual)
    # Check connected devices against arguments
    left_serial = None
    right_serial = None
    if args.left_serial != "":
        # If serials are specified then check they are connected
        TitaniaTest.checkSerialPairConnected(
            args.left_serial, args.right_serial)
        left_serial = args.left_serial
        right_serial = args.right_serial
    if args.left_serial == "":
        if args.titania_serial == "":
            # If serials are not specifed then
            # check only two cameras are connected and get their serials
            left_serial, right_serial = TitaniaTest.getSerialPairConnected()
        if args.titania_serial != "":
            # If titania serial is specified then
            # get the left and right camera from the unique serial.
            # Requires the camera is connected to read the valid serials.
            left_serial, right_serial = \
                TitaniaTest.getLeftRightSerialFromTitaniaSerial(
                    args.titania_serial)
    if left_serial is None or right_serial is None:
        # This shouldn't be possible as previous error checking
        # should always set serials or raise an exception
        raise Exception("Failed to get valid camera serials")
    external_serial_port = None
    if args.enable_external_serial:
        if args.external_serial_port == "":
            # Check if external serial device is avaiable
            external_serial_port = TitaniaTest.getFirstSerialDevice()
            if external_serial_port is None:
                raise Exception(
                    "Failed to find serial comms device for external data")
        else:
            serial_list = TitaniaTest.listAvailableSerialDevices()
            if args.external_serial_port not in serial_list:
                raise Exception(
                    "Failed to find specifed serial comms \
                        device for external data collection.")
            external_serial_port = args.external_serial_port

    # Define test parameters
    test_params = TitaniaTest.TitaniaTestParams(
        left_serial=left_serial, right_serial=right_serial,
        output_folderpath=args.output,
        capture_fps=args.capture_fps,
        save_fps=args.save_fps,
        save_images=(not args.disable_images),
        capture_temperature=(not args.disable_temp),
        enable_external_serial=(args.enable_external_serial),
        external_serial_port=external_serial_port,
        virtual_camera=args.virtual,
        timeout=args.timeout,
        left_exposure=args.left_exposure,
        right_exposure=args.right_exposure
    )
    TitaniaTest.validateTitaniaTestParams(test_params)
    # Run test
    exit_code = TitaniaTest.run(test_params)
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
