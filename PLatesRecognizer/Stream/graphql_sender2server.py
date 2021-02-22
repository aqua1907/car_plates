from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
import json
from configobj import ConfigObj
import dateutil.parser
import os
import datetime


def read_jsonl(path):
    """
    Read last record in JSONL file. Last record is a first line in the file.
    :param path: String. Path to the file
    :return: Dict
    """
    with open(path) as file_obj:  # read file
        line = next(iter(file_obj))  # get first line of file with results
        data = json.loads(line)  # load data
    file_obj.close()

    return data


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
    filename = config['cameras']['camera-1']['jsonlines_file']  # get filename of results
    params = dict()

    if os.path.exists(filename):  # check file with results exists
        if os.path.getsize(filename) > 0:  # check if file is not empty
            data = read_jsonl(filename)
            last_timestamp = dateutil.parser.isoparse(data["timestamp"])
            print(last_timestamp)
        else:
            last_timestamp = datetime.datetime.now().isoformat()    # if file is empty last time equals datetime.now()
    else:
        last_timestamp = datetime.datetime.now().isoformat()    # if file is does not exist time equals datetime.now()

    while True:
        if os.path.exists(filename):  # check file with results exists
            if os.path.getsize(filename) > 0:  # check if file is not empty
                data = read_jsonl(filename)
                new_timestamp = dateutil.parser.isoparse(data["timestamp"])
                t_delta = (new_timestamp - last_timestamp).total_seconds()
                if t_delta > 0:
                    last_timestamp = new_timestamp
                    # rename camera- to gate while keeping camera_id
                    data["camera_id"] = data["camera_id"].replace("camera-", "gate")
                    for result in data["results"]:
                        # Create queryString and pass as variable
                        params = '{"carColor": "%s", "carMark": "%s", "carNumber": "%s", ' \
                                 '"gateId": "%s", "id": "%s", "isFront": %s, ' \
                                 '"parkingId": "%s", "time": "%s"}' % ("", "", result["plate"],
                                                                       data["camera_id"], "", "true",
                                                                       "", data["timestamp"])

                    query = gql(query_code)
                    result = client.execute(query, variable_values={"params": params})  # Execute query
                    print(result)


if __name__ == "__main__":
    main()
