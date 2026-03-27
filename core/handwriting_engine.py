from PIL import Image
import json
import cv2
import numpy as np
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch

def deskew_image(pil_image):
    """Auto-rotate and deskew an image for better OCR."""
    # Force RGB uint8 so OpenCV never chokes on palette/RGBA modes
    img = np.array(pil_image.convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # --- Step 1: Fix major rotation (90/180/270) ---
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                            minLineLength=img.shape[1] // 4, maxLineGap=20)

    if lines is not None and len(lines) > 5:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            angles.append(angle)

        angles = np.array(angles)
        horizontal = np.sum((np.abs(angles) < 30) | (np.abs(angles) > 150))
        vertical = np.sum((np.abs(angles) > 60) & (np.abs(angles) < 120))

        if vertical > horizontal * 1.5:
            # Page is sideways — rotate 90° clockwise
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if len(img.shape) == 3 else img.copy()

    # --- Step 2: Fine deskew (small angle correction) ---
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80,
                            minLineLength=img.shape[1] // 4, maxLineGap=20)

    if lines is not None and len(lines) > 0:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angle) < 30:
                angles.append(angle)

        if angles:
            median_angle = np.median(angles)
            if abs(median_angle) > 0.5:
                h, w = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                img = cv2.warpAffine(img, M, (w, h),
                                     flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)

    # Resize to cap long edge at 1500px to avoid huge token counts
    result = Image.fromarray(img)
    max_side = max(result.size)
    if max_side > 2000:
        scale = 2000 / max_side
        result = result.resize((int(result.width * scale), int(result.height * scale)), Image.LANCZOS)
    return result


# Load model
def load_models():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    print(f"Using device: {device} | dtype: {dtype}")

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        trust_remote_code=True,
        dtype=dtype,
    ).to(device)
    processor = AutoProcessor.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        trust_remote_code=True,
        min_pixels=256 * 28 * 28,
        max_pixels=1024 * 28 * 28,
    )
    return model, processor, device


model, processor, device = load_models()


# Function for OCR and search
def ocr_and_search(image, keyword):

    # Deskew before OCR
    image = deskew_image(image)

    text_query = (
        "Perform OCR on this image. Read every piece of text visible in the image "
        "and output the recognized text only. Preserve the original line breaks and layout. "
        "Do NOT output bounding boxes, coordinates, or image descriptions."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": text_query},
            ],
        }
    ]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to(device)

    # Generate text
    with torch.no_grad():
        generated_ids = model.generate(**inputs, max_new_tokens=1024)
        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        extracted_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

    # Save extracted text to JSON
    output_json = {"query": text_query, "extracted_text": extracted_text}
    json_output = json.dumps(output_json, ensure_ascii=False, indent=4)

    # Perform keyword search
    keyword_lower = keyword.lower()
    sentences = extracted_text.split('. ')
    matched_sentences = [s for s in sentences if keyword_lower in s.lower()]

    return extracted_text, matched_sentences, json_output


def extract_handwriting(file_path):
    """Silent helper for Flask to process an image via Qwen-VL."""
    try:
        # Load the image from the file path provided by Flask
        image = Image.open(file_path)
        
        # We don't need the keyword search for grading, just the text
        extracted_text, _, _ = ocr_and_search(image, keyword="")
        
        return extracted_text.strip()
    except Exception as e:
        print(f"Qwen-VL Error: {e}")
        return f"[ERROR: Qwen-VL failed to read image - {str(e)}]"