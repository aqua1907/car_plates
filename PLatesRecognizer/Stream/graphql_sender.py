import datetime

import graphene
import json
import os
from graphene.types.generic import GenericScalar
from configobj import ConfigObj
import dateutil.parser


class CarInfo(graphene.ObjectType):
    """
        The class that describes all info about the car from the Platerecognizer results
    """
    plate = graphene.String()
    plateBbox = graphene.String()
    vehicleType = graphene.String()
    vehicleBbox = graphene.String()
    region = graphene.String()


class Query(graphene.ObjectType):
    """
        The class that represents schema for query execution
    """
    carInfo = graphene.Field(CarInfo, result=GenericScalar())
    camera = graphene.String(camera_id=graphene.String())  # add info about from which camera results were captured
    timestamp = graphene.String(time=graphene.String())

    def resolve_carInfo(self, info, result):
        """
        Details about car function resolver
        :param info: default parameter
        :param result: Dict from list results
        :return: field with all car information
        """
        return CarInfo(
            plate=result["plate"],
            plateBbox=result["box"],
            vehicleType=result["vehicle"]["type"],
            vehicleBbox=result["vehicle"]["box"],
            region=result["region"]['code'],
        )

    def resolve_camera(self, info, camera_id):
        """
        Get camera id function resolver
        :param info: default parameter
        :param camera_id: String, ex.: "camera-1"
        :return: String that represents camera id
        """
        return camera_id

    def resolve_timestamp(self, info, time):
        """
        Get car number registration time
        :param info: default parameter
        :param time: String, time in ISO format
        :return: Datetime in ISO format of car number registration time
        """
        return time


def read_jsonl(path):
    """
    Read last record in JSONL file. Last record is a first line in the file.
    :param path: String. Path to the file
    :return: Dict
    """
    with open(filename) as file_obj:  # read file
        line = file_obj.read().splitlines()[-1]  # get last line of file with results
        data = json.loads(line)  # load data
    file_obj.close()

    return data


if __name__ == "__main__":
    config = ConfigObj(r"config.ini")  # read Platerecognizer config file
    filename = config['cameras']['camera-1']['jsonlines_file']  # get filename of results

    # Build schema for query execution
    schema = graphene.Schema(query=Query)
    query = """
                query($result: GenericScalar,
                      $cameraId: String,
                      $time: String)
                {
                    camera(cameraId: $cameraId)
                    timestamp(time: $time)
                    carInfo(result: $result)
                    {
                        plate
                        plateBbox
                        vehicleType
                        vehicleBbox
                        region
                    }
                }
            """
    if os.path.exists(filename):  # check file with results exists
        if os.path.getsize(filename) > 0:  # check if file is not empty
            data = read_jsonl(filename)
            last_timestamp = dateutil.parser.isoparse(data["timestamp_local"])
            # print(last_timestamp)
        else:
            # if file is empty last time equals datetime.now()
            last_timestamp = datetime.datetime.now().astimezone().isoformat()
            last_timestamp = dateutil.parser.isoparse(last_timestamp)  # Convert str time iso format to datetime
    else:
        # if file is does not exist time equals datetime.now()
        last_timestamp = datetime.datetime.now().astimezone().isoformat()
        last_timestamp = dateutil.parser.isoparse(last_timestamp)   # Convert str time iso format to datetime

    print(last_timestamp)
    while True:
        if os.path.exists(filename):  # check file with results exists
            if os.path.getsize(filename) > 0:  # check if file is not empty
                data = read_jsonl(filename)
                new_timestamp = dateutil.parser.isoparse(data["timestamp_local"])
                t_delta = (new_timestamp - last_timestamp).total_seconds()
                if t_delta > 0:
                    last_timestamp = new_timestamp
                    for result in data["results"]:
                        # Loop for each detect plate and execute query with variables
                        out = schema.execute(query, variables={"cameraId": data["camera_id"],
                                                               "time": last_timestamp,
                                                               "result": result})
                        print(json.dumps(out.data, indent=4))
