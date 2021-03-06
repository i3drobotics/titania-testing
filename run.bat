@echo off

SET /A LEFT_SERIAL=40098266
SET /A RIGHT_SERIAL=40098271
SET /A LEFT_EXPOSURE=4000
SET /A RIGHT_EXPOSURE=4000
SET /A CAMERA_FPS=10

python run.py --left_serial %LEFT_SERIAL% --right_serial %RIGHT_SERIAL% ^
    --left_exposure %LEFT_EXPOSURE% --right_exposure %RIGHT_EXPOSURE% ^
    --capture_fps %CAMERA_FPS% --save_fps 10 --enable_external_serial --timeout 30.0 --output "./out/startup"
python run.py --left_serial %LEFT_SERIAL% --right_serial %RIGHT_SERIAL% ^
    --left_exposure %LEFT_EXPOSURE% --right_exposure %RIGHT_EXPOSURE% ^
    --capture_fps %CAMERA_FPS% --save_fps 0.1 --enable_external_serial --timeout 0.0 --output "./out/main"