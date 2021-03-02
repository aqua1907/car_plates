from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from configobj import ConfigObj
import json
import os


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
    x1, y1 = bbox["xmin"], bbox["ymin"]
    x2, y2 = bbox["xmax"], bbox["ymax"]

    h, w = x2 - x1, y2 - y1
    area = h * w

    return area


def main():
    token = ""
    query_code = """
                    mutation($params: String) {
                    createContainer(datatype:"RECDATA", data: $params)
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
    filename = config['cameras']['camera-2']['jsonlines_file']  # get filename of results

    if os.path.exists(filename):  # check file with results exists
        if os.path.getsize(filename) > 0:  # check if file is not empty
            data = read_jsonl(filename)
            last_filesize = os.path.getsize(filename)
            last_license_plate = data['results'][0]['plate']
        else:
            last_filesize = 0
            last_license_plate = ''
    else:
        last_filesize = 0
        last_license_plate = ''

    send = False
    counter_front = 0
    counter_back = 0

    while True:
        if os.path.exists(filename):  # check file with results exists
            if os.path.getsize(filename) > 0:  # check if file is not empty
                new_filesize = os.path.getsize(filename)
                if new_filesize > last_filesize:
                    last_filesize = new_filesize
                    data = read_jsonl(filename)
                    print(f"Counter front = {counter_front}")
                    print(f"Counter back = {counter_back}")

                    if data['results'][0]['vehicle']["score"] != 0.0:
                        new_license_plate = data['results'][0]['plate']
                        print(new_license_plate)
                        if new_license_plate != last_license_plate:
                            last_license_plate = new_license_plate
                            initial_bbox = data['results'][0]['box']
                            initial_box_area = compute_area(initial_bbox)
                            print(f"Initial bbox = {initial_box_area}")
                        else:
                            bbox = data['results'][0]['box']
                            box_area = compute_area(bbox)
                            print(f"bbox = {box_area}")

                            if box_area > initial_box_area:
                                counter_front += 1
                                if counter_front == 7:
                                    is_front = "true"
                                    send = True
                            elif box_area < initial_box_area:
                                counter_back += 1
                                if counter_back == 7:
                                    is_front = "false"
                                    send = True

                elif new_filesize == last_filesize:
                    if send:
                        data = read_jsonl(filename)
                        # rename camera- to gate while keeping camera_id
                        data["camera_id"] = data["camera_id"].replace("camera-", "gate")
                        result = data["results"][0]

                        # Create queryString and pass as variable
                        params = '{"carColor": "%s", "carMark": "%s", "carNumber": "%s", ' \
                                 '"gateId": "%s", "id": "%s", "isFront": %s, ' \
                                 '"parkingId": "%s", "time": "%s"}' % ("", "", result["plate"],
                                                                       data["camera_id"], "", is_front,
                                                                       "", data["timestamp_local"])

                        query = gql(query_code)
                        result = client.execute(query, variable_values={"params": params})  # Execute query
                        print(result)
                        send = False
                        counter_front = 0
                        counter_back = 0


if __name__ == "__main__":
    main()
