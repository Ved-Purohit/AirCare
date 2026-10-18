"""Threaded camera: always hands back the newest frame with its capture time (lowest latency)."""
import threading
import time
import cv2


class Camera:
    def __init__(self, index=0, width=640, height=480, fps=60):
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))   # lets webcams reach 60 fps
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.opened = self.cap.isOpened()
        self._lock = threading.Lock()
        self._frame, self._t, self._seq = None, 0.0, 0
        self._run = True
        if self.opened:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._run:
            ok, f = self.cap.read()
            if ok:
                with self._lock:
                    self._frame, self._t, self._seq = f, time.perf_counter(), self._seq + 1
            else:
                time.sleep(0.005)

    def read(self):
        """Returns (frame, capture_time, sequence_number); frame is None until the first arrives."""
        with self._lock:
            return self._frame, self._t, self._seq

    @property
    def fps(self):
        return self.cap.get(cv2.CAP_PROP_FPS)

    def release(self):
        self._run = False
        time.sleep(0.05)
        self.cap.release()
