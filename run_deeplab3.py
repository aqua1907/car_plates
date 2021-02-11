import cv2
import torch
import numpy as np
import torchvision.transforms as T
import os
import tensorflow as tf
import random
from timeit import default_timer as timer
from RectDetector import RectDetector
from pytorch_sergmentation.model import create_model
from utils.general import letterbox, normalize, decode_batch, thresh_callback


weights = r"D:\Projects\ML_projects\car_plates\weights\model_v2.pth"
image = r"examples\image_1.jpg"

device = torch.device("cpu")
half = device.type != "cpu"

model = create_model()
checkpoint = torch.load(weights, map_location=device)
model.load_state_dict(checkpoint["model"])
model.to(device)
model.eval()

if half:
    model.half()

preprocess = T.Compose([
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

rectDetector = RectDetector()

recognition = tf.keras.models.load_model(r"weights/anpr_ocr_eu_2020_10_14_tensorflow_v2.2.h5")
images = os.listdir(r"examples")
random.shuffle(images)

for image in images:
    image_path = os.path.join("examples", image)
    start = timer()

    frame = cv2.imread(image_path)
    frame, _, _ = letterbox(frame, 1000)

    img = preprocess(frame).unsqueeze(0).to(device)
    if half:
        img = img.half()

    output = model(img)["out"][0]
    masks = (output > .1)
    masks = masks.detach().cpu().numpy()
    masks = [thresh_callback((mask * 255).astype(np.uint8)) for mask in masks]
    cv2.imshow("mask", masks[0])

    arrPoints = rectDetector.detect(masks)

    # cut zones
    zones = rectDetector.get_cv_zonesRGB(frame, arrPoints, 295, 64)
    cv2.imshow("zones", zones[0])
    arrPoints = np.array(arrPoints).reshape((-1, 1, 2)).astype(np.int32)
    x1, y1 = arrPoints[0][0]

    x = normalize(zones[0])
    out = recognition.predict(x)

    text = decode_batch(out)[0]
    t_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
    x2, y2 = x1 + t_size[0], y1 - t_size[1] - 3

    end = timer()
    infer_time = end - start
    print(f"Inference time: {infer_time:.1f}s")
    cv2.drawContours(frame, [arrPoints], -1, (136, 157, 255), thickness=2, lineType=cv2.LINE_AA)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (136, 157, 255), -1)
    cv2.putText(frame, text, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, lineType=cv2.LINE_AA)
    cv2.imshow("window", frame)
    cv2.imwrite(r"results/" + image, frame)
    if cv2.waitKey(0) & 0xFF == ord('q'):
        break
