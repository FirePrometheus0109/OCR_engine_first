import json
import fitz
from geometry import BoundingBox
import math
from typing import Dict, List, Any
from PIL import Image
import io


def make_pdf_doc_searchable(
    pdf_doc: fitz.Document,
    textract_pages: List[Dict[str, Any]],
    add_word_bbox: bool = False,
    show_selectable_char: bool = False,
    pdf_image_dpi: int = 100,  # Adjust DPI to improve quality
    jpeg_quality: int = 85,    # Adjust JPEG quality
    verbose: bool = False,
) -> fitz.Document:
    """
    Convert a non-searchable PDF to a searchable one using Textract data.
    """
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

        # Convert pixmap to PIL image to apply compression
        img = Image.frombytes("RGB", (pdf_pix_map.width, pdf_pix_map.height), pdf_pix_map.samples)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=jpeg_quality)  # Adjust quality for compression
        img_byte_arr.seek(0)

        output_page = output_pdf.new_page(
            width=pdf_page.rect.width, height=pdf_page.rect.height
        )
        output_page.insert_image(pdf_page.rect, stream=img_byte_arr)

        for block in page_blocks.get(page_number, []):
            if block["BlockType"] == "WORD":
                bbox = BoundingBox.from_textract_bbox(block["Geometry"]["BoundingBox"])
                bbox.scale(output_page.rect.width, output_page.rect.height)

                # if add_word_bbox:
                #     pdf_rect = fitz.Rect(bbox.left, bbox.top, bbox.right, bbox.bottom)
                #     output_page.draw_rect(
                #         pdf_rect,
                #         color=(220 / 255, 20 / 255, 60 / 255),
                #         fill=None,
                #         width=0.7,
                #         dashes=None,
                #         overlay=True,
                #         morph=None,
                #     )

                fill_opacity = 1 if show_selectable_char else 0
                text = block["Text"]
                text_length = fitz.get_text_length(
                    text, fontname="helv", fontsize=15
                )
                fontsize_optimal = int(
                    math.floor((bbox.width / text_length) * 15)
                )
                output_page.insert_text(
                    point=fitz.Point(bbox.left, bbox.bottom),
                    text=text,
                    fontname="helv",
                    fontsize=fontsize_optimal,
                    rotate=0,
                    color=(220 / 255, 20 / 255, 60 / 255),
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
    pdf_image_dpi=100,  # Adjusted DPI for better quality
    verbose=True,
)

selectable_pdf_doc.save("output.pdf", garbage=4, deflate=True)  # Use deflate compression