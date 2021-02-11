import os
import random
import cv2
import numpy as np
import tensorflow as tf
from models.experimental import attempt_load
from utils.general import detect, get_characters, normalize, decode_batch
from utils.torch_utils import select_device
from RectDetector import RectDetector


def nested_change(item, func):
    if isinstance(item, list):
        return [nested_change(x, func) for x in item]
    return func(item)


device = select_device("")
half = device.type != 'cpu'

detection_weights = r"weights/detection_best.pt"
recognition_weights = r"weights/anpr_ocr_eu_2020_10_14_tensorflow_v2.2.h5"

lp_detection = attempt_load(detection_weights, map_location=device)
lp_recognition = tf.keras.models.load_model(recognition_weights)
# lp_recognition = attempt_load(recognition_weights, map_location=device)
# CLASSES = lp_recognition.module.names if hasattr(lp_recognition, 'module') else lp_recognition.names
rectDec = RectDetector()

lp_detection.to(device)

if half:
    lp_detection.half()
    # lp_recognition.half()

image_path = os.path.join(r"examples", "photo_2021-02-04_18-02-07.jpg")
frame = cv2.imread(image_path)
frame1 = frame.copy()
pred_lp = detect(frame, lp_detection, device, half, size=640, conf=0.6)
for license_plate in pred_lp:
    if license_plate is not None:
        for *xyxy, conf, cls in license_plate:
            x4, y4, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
            crop0 = frame[y4:y2, x4:x2]
            # arrPoints = np.array(arrPoints).reshape((-1, 1, 2)).astype(np.int32)
            # cv2.drawContours(frame1, [arrPoints], -1, (136, 157, 255), thickness=2, lineType=cv2.LINE_AA)

            # crop0 = frame[y1:y2, x1:x2]
            # crop0 = cv2.bilateralFilter(crop0, 11, 20, 20)
            # preds = detect(crop0, lp_recognition, device, half, size=288, conf=0.7, iou_tresh=0.7)
            # text = get_characters(crop0, preds, classes=CLASSES)
        img = normalize(crop0)
        out = lp_recognition.predict(img)
        text = decode_batch(out)[0]
        t_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 2)[0]
        #
        cv2.rectangle(frame, (x4, y4), (x2, y2), (137, 236, 255), 2, lineType=cv2.LINE_AA)
        x2, y2 = x4 + t_size[0], y4 - t_size[1] - 3
        cv2.rectangle(frame, (x4, y4), (x2, y2), (137, 236, 255), -1)
        cv2.putText(frame, text, (x4, y4 - 2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2, lineType=cv2.LINE_AA)

    cv2.imshow("original image", frame)
    cv2.imshow("crop0", crop0)
    if cv2.waitKey(0) & 0xFF == ord('q'):
        break

