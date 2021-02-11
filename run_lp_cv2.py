import cv2
import numpy as np
# import pytesseract


# get grayscale image
def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


# noise removal
def remove_noise(image):
    return cv2.medianBlur(image, 5)


# thresholding
def thresholding(image):
    return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


# dilation
def dilate(image):
    kernel = np.ones((5, 5), np.uint8)
    return cv2.dilate(image, kernel, iterations=1)


# erosion
def erode(image):
    kernel = np.ones((5, 5), np.uint8)
    return cv2.erode(image, kernel, iterations=1)


# opening - erosion followed by dilation
def opening(image):
    kernel = np.ones((5, 5), np.uint8)
    return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)


# canny edge detection
def canny(image):
    return cv2.Canny(image, 100, 200)


# skew correction
def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)

    else:
        angle = -angle
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return rotated


# pytesseract.pytesseract.tesseract_cmd = r'C:\Users\vanou\Tesseract-OCR\tesseract.exe'

img = cv2.imread(r'examples/photo_2021-02-04_18-02-07.jpg', cv2.IMREAD_COLOR)
orig = img.copy()

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gray = cv2.bilateralFilter(gray, 11, 17, 17)

edged = cv2.Canny(gray, 30, 200)
contours = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
screenCnt = None

for c in contours:
    peri = cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, 0.018 * peri, True)

    if len(approx) == 4:
        screenCnt = approx
        cv2.drawContours(img, [screenCnt], -1, (0, 0, 255), 2, cv2.LINE_AA)
        break

if screenCnt is None:
    detected = 0
    print("No contour detected")
else:
    detected = 1

# if detected == 1:
#     cv2.drawContours(img, [screenCnt], -1, (0, 0, 255), 2, cv2.LINE_AA)

# mask = np.zeros(gray.shape, np.uint8)
# new_image = cv2.drawContours(mask, [screenCnt], 0, 255, -1)
# out = np.zeros_like(img)  # Extract out the object and place into output image
# out[mask == 255] = img[mask == 255]

# (y, x) = np.where(mask == 255)
# (topy, topx) = (np.min(y), np.min(x))
# (bottomy, bottomx) = (np.max(y), np.max(x))
# out = out[topy:bottomy+1, topx:bottomx+1]

(x, y, w, h) = cv2.boundingRect(screenCnt)
cropped = gray[y:y + h, x:x + w]

pts = screenCnt.reshape(4, 2)
rect = np.zeros((4, 2), dtype="float32")
# the top-left point has the smallest sum whereas the
# bottom-right has the largest sum
s = pts.sum(axis=1)
rect[0] = pts[np.argmin(s)]
rect[2] = pts[np.argmax(s)]
# compute the difference between the points -- the top-right
# will have the minumum difference and the bottom-left will
# have the maximum difference
diff = np.diff(pts, axis=1)
rect[1] = pts[np.argmin(diff)]
rect[3] = pts[np.argmax(diff)]
# multiply the rectangle by the original ratio
# rect *= 1

# now that we have our rectangle of points, let's compute
# the width of our new image
(tl, tr, br, bl) = rect
widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
# ...and now for the height of our new image
heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
# take the maximum of the width and height values to reach
# our final dimensions
maxWidth = max(int(widthA), int(widthB))
maxHeight = max(int(heightA), int(heightB))
# construct our destination points which will be used to
# map the screen to a top-down, "birds eye" view
dst = np.array([
    [0, 0],
    [maxWidth - 1, 0],
    [maxWidth - 1, maxHeight - 1],
    [0, maxHeight - 1]], dtype="float32")
# calculate the perspective transform matrix and warp
# the perspective to grab the screen
M = cv2.getPerspectiveTransform(rect, dst)
warp = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))

warp = get_grayscale(warp)
warp = cv2.bilateralFilter(warp, 11, 17, 17)
# h, w = warp.shape[:2]
# warp = cv2.resize(warp, (w*2, h*2))
# warp = remove_noise(warp)
# warp = thresholding(warp)
# warp = dilate(warp)
# warp = erode(warp)
# warp = opening(warp)
# warp = canny(warp)
# warp = deskew(warp)


# text = pytesseract.image_to_string(warp, lang='eng', config='--psm 6')
# print("Detected license plate Number is:", text)
cv2.imshow('car', img)
cv2.imshow('Cropped', cropped)
cv2.imshow("warp", warp)

cv2.waitKey(0)
cv2.destroyAllWindows()
