import cv2

class VideoCapture:
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)
        self.start_time_offset = 0 #second
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.start_frame = int(self.start_time_offset * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
        self.prev_frame_time = 0
        self.new_frame_time = 0

    def set_start_time(self, start_time_offset):
        self.start_time_offset = start_time_offset
        self.start_frame = int(self.start_time_offset * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)

    def read_frame(self):
        success, frame = self.cap.read()
        if success:
            frame = cv2.resize(frame, (1280, 720))
        return frame

    def display_frame(self, frame):
        cv2.imshow("Image", frame)

    def forward_frame(self, frameNum):
        # Advance the video by 10 frame
        for _ in range(frameNum):
            self.read_frame()

    def back_frame(self, frameNum):
        # Go back 10 frames (if possible)
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        new_frame = max(0, current_frame - frameNum)  # Ensure not to go below frame 0
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
        img = self.read_frame()
        return img

    def set_newFrameTime(self, new_frame_time):
        self.new_frame_time = new_frame_time

    def get_fps(self):
        fps = 1 / (self.new_frame_time - self.prev_frame_time)
        self.prev_frame_time = self.new_frame_time
        return fps

    def is_open(self):
        return self.cap.isOpened()

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def get_current_timestamp(self):
        return self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000  # Convert to seconds
