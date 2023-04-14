import cv2
import numpy as np
import depthai as dai
from camera import Camera
from oak_camera_rvc3 import OakCamera
from numpy_replay_camera import NumpyReplayCamera
from utils import *
from depth_test import DepthTest
import config
import open3d as o3d
from pathlib import Path
np.seterr(invalid='raise')
if config.astra_gt:
    from astra_camera import AstraCamera
    from openni import openni2
    openni2.initialize()
depth_test = DepthTest()
cameras = []

if config.args.depth and config.args.rectified and config.args.calib:
    replay_camera = NumpyReplayCamera(
        Path(config.args.depth),
        Path(config.args.rectified),
        Path(config.args.calib)
    )
    cameras.append(replay_camera)
else:
    rvc3_camera = OakCamera(None, config.args.vertical)
    cameras.append(rvc3_camera)


if config.astra_gt:
    try:
        device_info = openni2.Device.open_any()
        astra_camera = AstraCamera(device_info)
        cameras.append(astra_camera)
    except:
        print("❗WARNING: Astra not found")

if len(cameras) == 0:
    print("❗ERROR: No cameras found")
    exit()

selected_camera = cameras[0]
testing = False
running = True
solid_color = False

def quit_callback():
    global running
    running = False

def start_test_callback():
    global testing
    if not depth_test.fitted:
        print("❗WARNING: Plane not fitted, using default values")

    print("Testing started ...")
    testing = True

def fit_plane_callback():
    # depth_test.fit_plane(selected_camera.point_cloud)
    depth_test.fit_plane_o3d(selected_camera.point_cloud)
    depth_test.print_tilt()
    # depth_test.visualize_plane_fit(point_cloud)

def select_camera_callback(id: int):
    global selected_camera
    if id < len(cameras) and id >= 0:
        selected_camera = cameras[id]
        print(f"Selected camera: {selected_camera.window_name}")

def save_point_clouds_callback():
    for camera in cameras:
        o3d.io.write_point_cloud(f"utilities/{camera.window_name}.ply", camera.point_cloud)

    print("Point clouds saved")

def visualize_plane_callback():
    if depth_test.plane_fit_visualization:
        depth_test.hide_plane_fit_visualization()
    else:
        print("Plane fit visualization")
        print(" - red - original fitted plane")
        print(" - green - corrected fitted plane")
        print(" - colored - corrected point cloud")
        depth_test.show_plane_fit_visualization(selected_camera.point_cloud)

def set_ground_truth_callback():
    distance = depth_test.set_ground_truth(selected_camera.point_cloud)
    print(f"Ground truth set to {distance} m")

def toggle_color_callback():
    global solid_color
    solid_color = not solid_color


def save_results_callback():
    name = selected_camera.mxid if hasattr(selected_camera, "mxid") else "unknown"
    depth_test.save_results(name)


def run_interaticve():
    global testing
    # point cloud visualization window
    point_cloud_window = o3d.visualization.VisualizerWithKeyCallback()
    point_cloud_window.create_window("Point Cloud")

    point_cloud_window.register_key_callback(ord('Q'), lambda vis: quit_callback())
    point_cloud_window.register_key_callback(ord('F'), lambda vis: fit_plane_callback())
    point_cloud_window.register_key_callback(ord('V'), lambda vis: visualize_plane_callback())
    point_cloud_window.register_key_callback(ord('T'), lambda vis: start_test_callback())
    point_cloud_window.register_key_callback(ord('G'), lambda vis: set_ground_truth_callback())
    point_cloud_window.register_key_callback(ord('P'), lambda vis: save_point_clouds_callback())
    point_cloud_window.register_key_callback(ord('C'), lambda vis: toggle_color_callback())
    point_cloud_window.register_key_callback(ord('1'), lambda vis: select_camera_callback(0))
    point_cloud_window.register_key_callback(ord('2'), lambda vis: select_camera_callback(1))

    for camera in cameras:
        point_cloud_window.add_geometry(camera.point_cloud)
    point_cloud_window.add_geometry(depth_test.plane_fit_pcl)
    point_cloud_window.add_geometry(depth_test.plane_fit_corrected_pcl)
    point_cloud_window.add_geometry(depth_test.point_cloud_corrected)
    point_cloud_window.get_view_control().set_constant_z_far(15)
    origin = o3d.geometry.TriangleMesh.create_coordinate_frame(size=1, origin=[0, 0, 0])
    point_cloud_window.add_geometry(origin)

    while running:
        key = cv2.waitKey(1)

        for camera, color in zip(cameras, [(1,0,0), (0,0,1)]):
            camera.update()
            if solid_color:
                camera.point_cloud.paint_uniform_color(color)
            point_cloud_window.update_geometry(camera.point_cloud)
        point_cloud_window.update_geometry(depth_test.plane_fit_pcl)
        point_cloud_window.update_geometry(depth_test.plane_fit_corrected_pcl)
        point_cloud_window.update_geometry(depth_test.point_cloud_corrected)

        point_cloud_window.poll_events()
        point_cloud_window.update_renderer()

        if testing:
            depth_test.measure(selected_camera)

            if depth_test.samples >= config.n_samples:
                testing = False
                depth_test.print_results()
                save_results_callback()
                selected_camera.save_roi()
                depth_test.reset()


if __name__ == "__main__":
    if config.mode == "measure":
        selected_camera.set_roi(config.roi)
        print(config.roi)
        for _ in range(config.n_samples):
            selected_camera.update()
            depth_test.measure(selected_camera)
        depth_test.print_results()
        save_results_callback()
    elif config.mode == "interactive":
        run_interaticve()
    else:
        print(f"{config.mode} is not a valid mode")