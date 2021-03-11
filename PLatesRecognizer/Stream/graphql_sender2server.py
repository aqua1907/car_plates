import datetime

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from configobj import ConfigObj
import json
import os
import cv2


def read_jsonl(path):
    """
    Read last record in JSONL file. Last record is a last line in the file.
    :param path: String. Path to the file
    :return: Dict
    """
    with open(path) as file_obj:  # read file
        line = file_obj.read().splitlines()[-1]  # get last line of file with results
        data = json.loads(line)  # load data
    file_obj.close()

    return data


def compute_area(bbox):
    """
    Compute area of bounding box by top left and right bottom coordinates
    :param bbox: (Dictionary) With 4 coordinates xyxy
    :return: (Float) area ob bbox
    """
    x1, y1 = bbox["xmin"], bbox["ymin"]
    x2, y2 = bbox["xmax"], bbox["ymax"]

    h, w = x2 - x1, y2 - y1
    area = h * w

    return area


def get_settings(path):
    """
    Read JSON file with given settings
    :param path: String. Path to the file
    :return: (Strings)
    """
    with open(path) as file_obj:
        settings = json.load(file_obj)
    file_obj.close()

    parking_id = settings["parkingId"]
    get_id = settings["getId"]
    camera_front = settings["cameraFront"]

    return parking_id, get_id, camera_front


def get_last_bbox(data):
    """
    Select last record in the result file and compute area of this last bounding box
    :param data: Dictionary of the JSON file
    :return: (Float) Computed area of the last bbox
    """
    last_bbox = data['results'][0]['box']
    last_box_area = compute_area(last_bbox)

    return last_box_area


def get_video_capture(url):
    """
    Create video capture from the given stream using OpenCV
    :param url: (Str) path to file, stream. (Int) choose a video device
    :return: capture scene, coder for video writer, size of the input video
    """
    cap = cv2.VideoCapture(url)
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
    size = (frame_width, frame_height)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    return cap, fourcc, size


def main():
    token = ""
    recdata_query = """
                    mutation($params: String) {
                    createContainer(datatype:"RECDATA", data: $params)
                      {
                        data
                      }
                    }
                 """

    recfree_query = """
                    mutation($params: String) {
                    createContainer(datatype:"RECFREE", data: $params)
                      {
                        data
                      }
                    }
                 """

    # Create connection to the server
    transport = RequestsHTTPTransport(url="http://188.166.82.231:9900/graphql", retries=3)
    # Create client object and fetch schema from server
    client = Client(transport=transport, fetch_schema_from_transport=True)

    config = ConfigObj(r"config.ini")  # read Platerecognizer config file
    filename = config['cameras']['camera-1']['jsonlines_file']  # get filename of results

    if os.path.exists(filename):  # check file with results exists
        if os.path.getsize(filename) > 0:  # check if file is not empty
            data = read_jsonl(filename)
            # Get last size of the file and last record of car licence plate
            last_filesize = os.path.getsize(filename)
            last_license_plate = data['results'][0]['plate']
        else:
            last_filesize = 0
            last_license_plate = ''
    else:
        last_filesize = 0
        last_license_plate = ''

    parking_id, gate_id, camera_front = get_settings(r"settings.json")

    rec_data = False
    rec_free = False
    counter_front = 0
    counter_back = 0

    url = config['cameras']['camera-1']['url']
    cap, fourcc, size = get_video_capture(url)
    last_time = datetime.datetime.now()     # get present time for comparison in the future
    timestamp = last_time.strftime("%d-%m-%y_%H-%M-%S")  # conver datetime to string
    # Create video writer object with given parameters
    writer = cv2.VideoWriter(r"results/{}.avi".format(timestamp), fourcc, 30.0, size)

    while cap.isOpened():
        new_time = datetime.datetime.now()  # current time to check every hour
        t_delta = (new_time - last_time).total_seconds()

        ret, frame = cap.read()
        # If ret is true. If the frame is reading correctly then save frame to video file
        if ret:
            writer.write(frame)
            if t_delta >= 3600:     # After one hour of recorded video create a new video file
                timestamp = new_time.strftime("%d-%m-%y_%H-%M-%S")
                writer.release()
                writer = cv2.VideoWriter(r"results/{}.avi".format(timestamp), fourcc, 30.0, size)
        else:
            print("Camera stream not detected")
        if os.path.exists(filename):  # check file with results exists
            if os.path.getsize(filename) > 0:  # check if file is not empty
                new_filesize = os.path.getsize(filename)
                # Update last file's size if true and read data
                if new_filesize > last_filesize:
                    last_filesize = new_filesize
                    data = read_jsonl(filename)

                    if data['results'][0]['vehicle']["score"] != 0.0:   # check car was recognized
                        new_license_plate = data['results'][0]['plate']
                        # If get new license plat it will compute initial area of bbox of plate
                        if new_license_plate != last_license_plate:
                            last_license_plate = new_license_plate
                            last_box_area = get_last_bbox(data)
                        # Condition. if the same vehicle re-enter or re-exit
                        elif counter_front == 0 and counter_back == 0:
                            last_box_area = get_last_bbox(data)
                        else:
                            # For the same license plate compute area of bboxes to detect if vehicle
                            # is approaching or driving away
                            bbox = data['results'][0]['box']
                            box_area = compute_area(bbox)
                            print(f"bbox = {box_area}")

                            # Need to count a certain amount of frames(records in the file) to
                            # to detect if vehicle is approaching or driving away
                            if box_area > last_box_area:
                                last_box_area = box_area
                                counter_front += 1
                                if counter_front == 7:
                                    is_front = "true"
                                    rec_data = True
                            elif box_area < last_box_area:
                                last_box_area = box_area
                                counter_back += 1
                                if counter_back == 7:
                                    is_front = "false"
                                    rec_data = True
                # if get same file size and has send=True than create a query and send to the server
                elif new_filesize == last_filesize:
                    if rec_data:
                        data = read_jsonl(filename)
                        result = data["results"][0]

                        # Create queryString and pass as variable
                        params = '{"carColor": "%s", "carMark": "%s", "carNumber": "%s", ' \
                                 '"gateId": "%s", "id": "%s", "isFront": %s, ' \
                                 '"parkingId": "%s", "time": "%s"}' % ("", "", result["plate"],
                                                                       gate_id, "", is_front,
                                                                       parking_id, data["timestamp_local"])

                        query = gql(recdata_query)
                        result = client.execute(query, variable_values={"params": params})  # Execute query

                        # print(result)
                        rec_data = False
                        rec_free = True
                        counter_front = 0
                        counter_back = 0
                    elif rec_free:
                        data = read_jsonl(filename)

                        # Create queryString and pass as variable
                        params = '{"parkingId": "%s", "time": "%s"}' % (parking_id, data["timestamp_local"])
                        query = gql(recfree_query)
                        result = client.execute(query, variable_values={"params": params})  # Execute query


if __name__ == "__main__":
    main()
