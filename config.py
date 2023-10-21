from backend.db_controller import DbController
import multiprocessing
from multiprocessing import Manager


prevPosTable = "prev_pos"
actionTable = "ChickenAction"
analysisTable = "ChickenAnalysis"
chickenActionLog = "action_log"
dbController = DbController()
standard_speed = 0.3  # 0.3 being the base speed that testing is done on
speed_ratio = 1  # for each frame
frame_num = 20  # per second based on the video
frame_skipped = 5  # how many frame is moved after finish processing 1 frame

chicken_num = 10
