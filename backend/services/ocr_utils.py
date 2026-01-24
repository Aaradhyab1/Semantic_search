import cv2
import numpy as np
from paddleocr import PaddleOCR
import logging

logger = logging.getLogger(__name__)

# Singleton OCR model (heavy, load once)
_ocr = PaddleOCR(
    lang="en",
    use_angle_cls=True,         # helps in detecting text of different angles
    det=True,
    rec=True
)

def preprocess_image(img: np.ndarray) -> np.ndarray:    # takes an image as a numpy array and returns a binary image
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)        # convert to grayscale
    gray = cv2.medianBlur(gray, 3)                # blur the image to remove noise

    _, thresh = cv2.threshold(                          # converts the image to pure black and white and automatically finds the best threshold
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return thresh

def run_ocr(img: np.ndarray) -> str:                    # takes an image as a numoy array and returns the OCR output
    result = _ocr.ocr(img, cls=True)                    # using the OCR model, detects text in the image

    lines = []
    for block in result:
        for line in block:
            lines.append(line[1][0])                    # only appends the recognized text

    return "\n".join(lines)
