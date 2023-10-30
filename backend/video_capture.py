import cv2

class VideoCapture:
    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(self.video_path)

    def read_frame(self):
        success, frame = self.cap.read()
        if success:
            frame = cv2.resize(frame, (1280, 720))
        if not success:
            return None
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

    def is_open(self):
        return self.cap.isOpened()

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()
