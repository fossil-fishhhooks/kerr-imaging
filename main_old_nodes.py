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




def setup():
    print(f'Cameras: {Photometrics.list_cameras()} \nConnecting to first...')
    # Connect to the camera
    cam = Photometrics.PvcamCamera()

    cam.open()
    print('Connected \nSetting up...')
    #cam.set_roi(0,18,0,18,1,1)
    print(cam.get_roi())
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

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Live Feed and Snapshot")
        self.setFixedSize(670, 800)  # Fixed window size

        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Live feed group
        self.live_group = QGroupBox("Live")
        live_layout = QVBoxLayout()
        self.live_label = QLabel(self)
        self.live_label.setFixedSize(316*2, 185*2)  # Fixed size for live feed, perfect aspect ratio
        self.live_label.setAlignment(Qt.AlignCenter)
        live_layout.addWidget(self.live_label)
        self.live_group.setLayout(live_layout)

        # Saved snap group
        self.snap_group = QGroupBox("Saved Snap")
        snap_layout = QHBoxLayout()



        # Take picture button
        self.snap_button = QPushButton("Take Picture")
        self.snap_button.setFixedSize(100, 30)
        self.snap_button.clicked.connect(self.take_snapshot)

        self.clear_button = QPushButton("Clear Picture")
        self.clear_button.setFixedSize(100, 30)
        self.clear_button.clicked.connect(self.clear_snapshot)

        # Snapshot feed
        self.snap_label = QLabel(self)
        self.snap_label.setFixedSize(int(316*1.2), int(185*1.2))  # Fixed size for saved snap not perfect aspect, but close
        self.snap_label.setAlignment(Qt.AlignCenter)

        self.log = QTextEdit()
        self.log.setReadOnly(True)  # Make it read-only
        self.log.setFixedHeight(100)  # Limit height
        self.log.setPlaceholderText("Log messages will appear here...")
        self.logtext = ""

        # Add button and snapshot to snap layout
        snap_layout.addWidget(self.snap_button)
        snap_layout.addWidget(self.clear_button)
        snap_layout.addWidget(self.snap_label)
        self.snap_group.setLayout(snap_layout)



        # Add widgets to the main layout
        main_layout.addWidget(self.live_group)
        main_layout.addWidget(self.snap_group)
        main_layout.addWidget(self.log)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Timer for live update
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1000 // 50)  # 50 FPS MAXIMUM

        self.snapshot = np.zeros((2960, 5056), dtype=np.uint8)
        height, width = self.snapshot.shape
        q_image = QImage(self.snapshot, width, height, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image).scaled(self.snap_label.width(), self.snap_label.height(),Qt.KeepAspectRatio)
        self.snap_label.setPixmap(pixmap)

        cam.setup_acquisition(mode="sequence")

        cam.start_acquisition()
    def update_frame(self):
        try:
            """Updates the live feed."""
            cam.wait_for_frame()  # wait for the next available frame
            self.framebuffer = cam.read_oldest_image()  # get the oldest image which hasn't been read yet


            self.display_frame(self.framebuffer, self.live_label)

        except Exception as e:
            self.logtext += "\n[ERROR] "
            self.logtext += str(e)

            self.log.setText(self.logtext)

    def take_snapshot(self):
        try:
            self.logtext += "\nSnap pressed"
            self.log.setText(self.logtext)
            """Captures and displays a snapshot."""
            self.snapshot = self.framebuffer.copy()
            self.display_frame(self.snapshot, self.snap_label)
            self.logtext += "\nDrew snap"
            self.log.setText(self.logtext)
        except Exception as e:
            self.logtext += "\n[ERROR] "
            self.logtext += str(e)

            self.log.setText(self.logtext)

    def clear_snapshot(self):
        try:
            self.logtext += "\nClear pressed"
            self.log.setText(self.logtext)
            self.snapshot = np.zeros((2960, 5056), dtype=np.uint8)
            height, width = self.snapshot.shape
            q_image = QImage(self.snapshot, width, height, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image).scaled(self.snap_label.width(), self.snap_label.height(), Qt.KeepAspectRatio)
            self.snap_label.setPixmap(pixmap)
            self.logtext += "\nSnap cleared"
            self.log.setText(self.logtext)
        except Exception as e:
            self.logtext += "\n[ERROR] "
            self.logtext += str(e)

            self.log.setText(self.logtext)

    def display_frame(self, frame, label):
        """Converts and displays a frame in a QLabel."""
        try:
            normalized_frame = ((frame / frame.max()) * 255).astype(np.uint8)  # Normalize to 8-bit
            height, width = normalized_frame.shape
            q_image = QImage(normalized_frame, width, height, QImage.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image).scaled(label.width(), label.height(), Qt.KeepAspectRatio)
            label.setPixmap(pixmap)
        except Exception as e:
            self.logtext += "\n[ERROR] "
            self.logtext += str(e)

            self.log.setText(self.logtext)


if __name__ == "__main__":


    app = QApplication(sys.argv)
    window = FramebufferWindow(cam)
    window.show()
    sys.exit(app.exec_())

