import cv2
import requests
from pprint import pprint
import json
import os

# image_path = r"examples/image_23.jpg"
# regions = ['ua', 'it', 'gr']  # Change to your country
# with open(image_path, 'rb') as fp:
#     response = requests.post(
#         'https://api.platerecognizer.com/v1/plate-reader/',
#         data=dict(regions=regions),  # Optional
#         files=dict(upload=fp),
#         headers={'Authorization': 'Token c530b59adc13692e778da84290353d9edd04de02'},
#         )
# data = response.json()
# pprint(data)
image_dir = r"PLatesRecognizer/Stream/camera-1_screenshots/21-02-08"

with open(r"PLatesRecognizer/Stream/camera-1_21-02-08.jsonl") as jsonl:
    for line in jsonl:
        data = json.loads(line)
        image_path = os.path.join(image_dir, data['filename'])
        frame = cv2.imread(image_path)
        for result in data['results']:
            x1, y1, x2, y2 = [v for k, v in result["box"].items()]
            plate = result["plate"].upper()
            t_size = cv2.getTextSize(plate, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]

            # cv2.rectangle(frame, (x1, y1), (x2, y2), (137, 236, 255), 2, lineType=cv2.LINE_AA)
            x2, y2 = x1 + t_size[0], y1 - t_size[1] - 3
            cv2.rectangle(frame, (x1, y1), (x2, y2), (137, 236, 255), -1)
            cv2.putText(frame, plate, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, lineType=cv2.LINE_AA)

        cv2.imshow("frame", frame)
        cv2.imwrite(os.path.join(r"results", data['filename']), frame)
        cv2.waitKey(0)

jsonl.close()