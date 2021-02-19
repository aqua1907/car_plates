import graphene
import json
from graphene.types.generic import GenericScalar
from configobj import ConfigObj
import os


class CarInfo(graphene.ObjectType):
    """
        The class that describes all info about the car from the Platerecognizer results
    """
    plate = graphene.String()
    plateBbox = GenericScalar()
    vehicleType = graphene.String()
    vehicleBbox = GenericScalar()
    region = graphene.String()


class Query(graphene.ObjectType):
    """
        The class that represents schema for query execution
    """
    carInfo = graphene.Field(CarInfo, results=GenericScalar())
    camera = graphene.String(camera_id=graphene.String())  # add info about from which camera results were captured

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


if __name__ == "__main__":
    config = ConfigObj(r"config.ini")  # read Platerecognizer config file
    filename = config['cameras']['camera-1']['jsonlines_file']  # get filename of results

    # Build schema for query execution
    schema = graphene.Schema(query=Query)
    query = """
                query($result: GenericScalar,
                      $cameraId: String)
                {
                    camera(cameraId: $cameraId)
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
    while True:
        if os.path.exists(filename):  # check file with results exists
            if os.path.getsize(filename) > 0:  # check if file is not empty
                with open(filename) as file_obj1:  # read file
                    line = next(iter(file_obj1))  # get first line of file with results
                    data = json.loads(line)  # load data
                    for result in data["results"]:
                        # Loop for each detect plate and execute query with variables
                        out = schema.execute(query, variables={"cameraId": data["camera_id"],
                                                               "result": result})
                        print(json.dumps(out.data, indent=4))
