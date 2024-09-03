import json
import fitz
from geometry import BoundingBox
import math
from typing import Dict, List, Any
from PIL import Image
import io


def calculate_rotation(polygon):
    top_left = polygon[0]
    top_right = polygon[1]
    delta_y = top_right['Y'] - top_left['Y']
    delta_x = top_right['X'] - top_left['X']
    angle = math.degrees(math.atan2(delta_y, delta_x))

    if -45 <= angle < 45:
        return 0
    elif 45 <= angle < 135:
        return 90
    elif angle >= 135 or angle < -135:
        return 180
    else:
        return 270


def make_pdf_doc_searchable(
    pdf_doc: fitz.Document,
    textract_pages: List[Dict[str, Any]],
    add_word_bbox: bool = False,
    show_selectable_char: bool = False,
    pdf_image_dpi: int = 100,
    jpeg_quality: int = 85,
    verbose: bool = False,
) -> fitz.Document:
    output_pdf = fitz.open()
    page_blocks = {}

    for page_number, page_blocks_list in enumerate(textract_pages):
        for block in page_blocks_list.get("Blocks", []):
            if page_number not in page_blocks:
                page_blocks[page_number] = []
            page_blocks[page_number].append(block)

    for page_number in range(len(pdf_doc)):
        pdf_page = pdf_doc.load_page(page_number)
        pdf_pix_map = pdf_page.get_pixmap(dpi=pdf_image_dpi, colorspace="RGB")

        img = Image.frombytes("RGB", (pdf_pix_map.width, pdf_pix_map.height), pdf_pix_map.samples)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=jpeg_quality)
        img_byte_arr.seek(0)

        output_page = output_pdf.new_page(
            width=pdf_page.rect.width, height=pdf_page.rect.height
        )
        output_page.insert_image(pdf_page.rect, stream=img_byte_arr)

        for block in page_blocks.get(page_number, []):
            if block["BlockType"] == "WORD":
                bbox = BoundingBox.from_textract_bbox(block["Geometry"]["BoundingBox"])
                bbox.scale(output_page.rect.width, output_page.rect.height)

                rotation_angle = calculate_rotation(block["Geometry"]["Polygon"])

                text = block["Text"]
                text_length = fitz.get_text_length(text, fontname="helv", fontsize=15)
                fontsize_optimal = int(math.floor((bbox.width / text_length) * 15))

                # Adjust the starting point for text insertion based on rotation and alignment
                if rotation_angle == 0:
                    text_point = fitz.Point(bbox.left, bbox.bottom)
                elif rotation_angle == 90:
                    text_point = fitz.Point(bbox.right, bbox.top)
                elif rotation_angle == 180:
                    text_point = fitz.Point(bbox.right, bbox.top - bbox.height)
                else:  # 270 degrees
                    text_point = fitz.Point(bbox.left, bbox.top)

                output_page.insert_text(
                    point=text_point,
                    text=text,
                    fontname="helv",
                    fontsize=fontsize_optimal,
                    rotate=rotation_angle,
                    color=(0, 0, 0),
                    fill_opacity=1 if show_selectable_char else 0,
                )

    pdf_doc.close()
    return output_pdf


doc = fitz.open("input.pdf")
data = json.load(open("response.json"))

textract_pages = [page_data for page_data in data]

print(f"no. of pages {len(textract_pages)}")

num_word_blocks = 0
for page_data in textract_pages:
    for blk in page_data.get("Blocks", []):
        if blk["BlockType"] == "WORD":
            num_word_blocks += 1
print(f"number of WORD blocks {num_word_blocks}")

selectable_pdf_doc = make_pdf_doc_searchable(
    pdf_doc=doc,
    textract_pages=textract_pages,
    add_word_bbox=False,
    show_selectable_char=False,
    pdf_image_dpi=100,
    jpeg_quality=85,
    verbose=True,
)

selectable_pdf_doc.save("output.pdf", garbage=4, deflate=True)