LEFT_SERIAL="40098272"
RIGHT_SERIAL="40098282"
EXTERNAL_SERIAL="COM5"
LEFT_EXPOSURE=4000.0
RIGHT_EXPOSURE=4000.0
CAMERA_FPS=10

python run.py --left_serial "$LEFT_SERIAL" --right_serial "$RIGHT_SERIAL" \
    --left_exposure $LEFT_EXPOSURE --right_exposure $RIGHT_EXPOSURE \
    --enable_external_serial --external_serial_port "$EXTERNAL_SERIAL" \
    --disable_images \
    --capture_fps $CAMERA_FPS --save_fps 0.1 --timeout 0.0 --output "./out/main"