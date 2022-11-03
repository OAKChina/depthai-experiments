import depthai as dai
import threading
import contextlib
import cv2
import time

# This can be customized to pass multiple parameters
def getPipeline(stereo):
    # Start defining a pipeline
    pipeline = dai.Pipeline()

    # Define a source - color camera
    cam_left = pipeline.create(dai.node.ColorCamera)
    cam_left.setBoardSocket(dai.CameraBoardSocket.LEFT)

    cam_right = pipeline.create(dai.node.ColorCamera)
    cam_right.setBoardSocket(dai.CameraBoardSocket.LEFT)

    stereoDepth = pipeline.create(dai.node.StereoDepth)
    cam_right.
    stereoDepth.

def worker(dev_info, stack, dic):
    openvino_version = dai.OpenVINO.Version.VERSION_2021_4
    device: dai.Device = stack.enter_context(dai.Device(openvino_version, dev_info, False))

    # Note: currently on POE, DeviceInfo.getMxId() and Device.getMxId() are different!
    print("=== Connected to " + dev_info.getMxId())
    mxid = device.getMxId()
    cameras = device.getConnectedCameras()
    usb_speed = device.getUsbSpeed()
    print("   >>> MXID:", mxid)
    print("   >>> Cameras:", *[c.name for c in cameras])
    print("   >>> USB speed:", usb_speed.name)

    device.startPipeline(getPipeline(len(cameras)==3))
    dic["rgb-" + mxid] = device.getOutputQueue(name="rgb")

device_infos = dai.Device.getAllAvailableDevices()
print(f'Found {len(device_infos)} devices')



with contextlib.ExitStack() as stack:
    queues = {}
    threads = []
    for dev in device_infos:
        time.sleep(1) # Currently required due to XLink race issues
        thread = threading.Thread(target=worker, args=(dev, stack, queues))
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join() # Wait for all threads to finish

    while True:
        for name, queue in queues.items():
            if queue.has():
                cv2.imshow(name, queue.get().getCvFrame())
        if cv2.waitKey(1) == ord('q'):
            break

print('Devices closed')