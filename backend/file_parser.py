from fastapi import UploadFile
import pdfplumber
import docx
import logging
import numpy as np
import cv2
from pdf2image import convert_from_bytes
#from .ocr_utils import preprocess_image, run_ocr

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 50  # threshold to decide OCR fallback. Selected 50 as it is a reasonable value.

"""
this function extracts text from a file depending on its extension. If the extension is pdf and the scanned text has a length 
less than MIN_TEXT_LENGTH, it falls back to OCR. Meaning that the pdf that was uploaded was scanned and not written. 
"""

def extract_text(file: UploadFile) -> str:
    file.file.seek(0)
    filename = file.filename.lower()

    try:
        if filename.endswith(".pdf"):
            # We strictly use standard text extraction now
            return _extract_pdf_text(file)

        elif filename.endswith(".docx"):
            return _extract_docx(file)

        elif filename.endswith(".txt"):
            return _extract_txt(file)

        else:
            # If someone uploads an image, we handle it gracefully instead of crashing
            return "OCR is currently disabled. Please upload a text-based PDF, Docx, or TXT file."

    except Exception as e:
        logger.exception("Text extraction failed")
        raise RuntimeError("Failed to extract text") from e

# Functions for extracting texts from different file formats

def _extract_pdf_text(file: UploadFile) -> str:
    text_blocks = []

    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()             # extracts text from each page
            if page_text:
                text_blocks.append(page_text)           # if text is not empty, append it to text_blocks

    return "\n".join(text_blocks)                       # at the end it returns a string with all the extracted text


def _extract_pdf_ocr(file: UploadFile) -> str:
    images = convert_from_bytes(file.file.read())       # reads the entire pdf as bytes and uses that to render each page as an image
    text_blocks = []

    for page in images:
        img = np.array(page)                            # converting the page into a numpy array
        processed = preprocess_image(img)               # using the preprocess_image function to preprocess the image
        ocr_text = run_ocr(processed)                   # using the run_ocr function to extract text from the image
        if ocr_text.strip():
            text_blocks.append(ocr_text)                # if the extracted text is not empty, append it to text_blocks

    return "\n".join(text_blocks)


def _extract_image_ocr(file: UploadFile) -> str:
    image_bytes = file.file.read()                      # read the image as bytes
    img_array = np.frombuffer(image_bytes, np.uint8)    # convert the bytes to an array
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)     # decoding the image using OpenCV

    processed = preprocess_image(img)                   # cleaning the image using the preprocess_image function
    return run_ocr(processed)


def _extract_docx(file: UploadFile) -> str:
    doc = docx.Document(file.file)                      # read the docx file
    return "\n".join(p.text for p in doc.paragraphs)    # iterating over the paragraphs and returning their text after joining them


def _extract_txt(file: UploadFile) -> str:
    return file.file.read().decode("utf-8", errors="ignore")    # read the txt file as bytes and decode it using utf-8
