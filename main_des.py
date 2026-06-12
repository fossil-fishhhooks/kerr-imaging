import pylablib as pll
from pylablib.devices import Photometrics
import matplotlib.pyplot as plt
import numpy as np
import sys
from PyQt5.QtWidgets import (
    QApplication, QLabel, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QGroupBox, QTextEdit
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5 import uic



def setup():
    try:
        print(f'Cameras: {Photometrics.list_cameras()} \nConnecting to first...')
        # Connect to the camera
        cam = Photometrics.PvcamCamera()
    except Exception as e:
        print("Uh oh! Can't connect to camera. Did you turn it on? Check device manager. If there is a message, kick the empty PCIE port device, and reboot.")
        exit(9)
    cam.open()
    print('Connected \nSetting up...')
    #cam.set_roi(0,18,0,18,1,1)
    print(f'Camera frame size: {cam.get_roi()[1]}x{cam.get_roi()[3]}')
    print(f'Camera frame timings: {cam.get_frame_timings()}')
    # Set exposure time (in milliseconds)
    #cam.set_exposure(10E-3)  # set 10ms exposure

    #cam.start_acquisition(mode='snap', nframes=1)


    return cam



def close(camera):
    camera.close()



NoI = 50

cam = setup()
framebuffer = np.zeros((2960, 5056), dtype=np.uint16)
framebuffer = cam.grab()[0]


class FramebufferWindow(QMainWindow):
    def __init__(self, cam):
        super().__init__()
        self.cam = cam  # Camera object
        self.framebuffer = self.cam.grab()[0]  # Initial frame
        self.snapshot = None  # Stores the snapshot image

        # Load the UI
        uic.loadUi("main-des.ui", self)  # Load the UI file

        # Access widgets by their objectName


        if self.snap_button is not None:

            self.snap_button.clicked.connect(self.take_snapshot)
        else:
            print("Uh oh! Can't bind to UI button (snap). Check names and things in designer.")
        if self.clear_button is not None:

            self.clear_button.clicked.connect(self.clear_snapshot)
        else:
            print("Uh oh! Can't bind to UI button (clear). Check names and things in designer.")

        self.logtext = ""  # Initialize logtext

        # Timer for live update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1000 // 50)  # 50 FPS MAXIMUM

        self.snapshot = np.zeros((2960, 5056), dtype=np.uint8)
        height, width = self.snapshot.shape
        q_image = QImage(self.snapshot, width, height, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image).scaled(self.snap_label.width(), self.snap_label.height(), Qt.KeepAspectRatio)
        self.snap_label.setPixmap(pixmap)

        cam.setup_acquisition(mode="sequence")
        cam.start_acquisition()


    def update_frame(self):
        try:
            #print("Updating frame...")
            cam.wait_for_frame()  # Wait for the next available frame, not necessary, but keep updating why not
            self.framebuffer = cam.read_oldest_image()  # Get the oldest image
            self.display_frame(self.framebuffer, self.live_label)

            scrollbar = self.log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:

            self.logtext += "\n[ERROR] " + str(e)
            self.log.setText(self.logtext)

    def take_snapshot(self):
        try:
            #print("Taking snapshot...")
            self.logtext += "\n[INFO] Snap pressed"
            self.log.setText(self.logtext)
            self.snapshot = self.framebuffer.copy()
            self.display_frame(self.snapshot, self.snap_label)
            self.logtext += "\n[INFO] Drew snap"
            self.log.setText(self.logtext)
        except Exception as e:

            self.logtext += "\n[ERROR] " + str(e)
            self.log.setText(self.logtext)

    def clear_snapshot(self):
        try:
            #print("Clearing snapshot...")
            self.logtext += "\n[INFO] Clear pressed"
            self.log.setText(self.logtext)
            self.snapshot = np.zeros((2960, 5056), dtype=np.uint8)
            height, width = self.snapshot.shape
            q_image = QImage(self.snapshot, width, height, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image).scaled(self.snap_label.width(), self.snap_label.height(), Qt.KeepAspectRatio)
            self.snap_label.setPixmap(pixmap)
            self.logtext += "\n[INFO] Snap cleared"
            self.log.setText(self.logtext)
        except Exception as e:

            self.logtext += "\n[ERROR] " + str(e)
            self.log.setText(self.logtext)

    def display_frame(self, frame, label):
        """Converts and displays a frame in a QLabel."""
        try:
            # Normalize the frame for display
            normalized_frame = ((frame / frame.max()) * 255).astype(np.uint8)
            height, width = normalized_frame.shape
            q_image = QImage(normalized_frame.data, width, height, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image).scaled(label.width(), label.height(), Qt.KeepAspectRatio)
            label.setPixmap(pixmap)
        except Exception as e:
            if (type(e) != AttributeError):
                self.logtext += "\n[ERROR] " + str(e)
                self.log.setText(self.logtext)
            else:
                self.logtext += "\n[ERROR] " + " Dropped frame because frame object was not set properly [framebuffer = NULL]"
                self.log.setText(self.logtext)


if __name__ == "__main__":


    app = QApplication(sys.argv)
    window = FramebufferWindow(cam)
    window.show()
    sys.exit(app.exec_())

