prevPosTable = "prev_pos"
actionTable = "chicken_action"
analysisTable = "analysis"
chickenActionLog = "action_log"
chickenList = "chicken_list"
trackLog = "track_log"

standard_speed = 0.3  # 0.3 being the base speed that testing is done on
speed_ratio = 1  # for each frame
frame_num = 20  # per second based on the video
frame_skipped = 2  # how many frame is moved after finish processing 1 frame

chicken_num = 10

green_color = (0, 252, 124)
red_color = (0, 0, 255)
yellow_color = (0, 255, 255)
blue_color = (255, 0, 0)
light_blue_color = (255, 255, 0)
black_color = (0, 0, 0)
white_color = (255, 255, 255)

bbox_color = {i: green_color for i in range(1, chicken_num + 1)}  # green

selected_chicken_id = 1
view_all = True

update_action_threshold = 5  # frame