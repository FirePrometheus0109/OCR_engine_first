import json
import fitz  # PyMuPDF
from geometry import BoundingBox
import math
from typing import Dict, List, Any

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
    verbose: bool = False,
) -> fitz.Document:
    # Create a new PDF for the output
    output_pdf = fitz.open()

    # Iterate over each page and add text overlay
    for page_number, page in enumerate(textract_pages):
        # Open the original page
        pdf_page = pdf_doc[page_number]

        # Create a new page with the same size
        output_page = output_pdf.new_page(width=pdf_page.rect.width, height=pdf_page.rect.height)

        # Copy non-text (e.g., images, graphics) content from the original page
        output_page.show_pdf_page(pdf_page.rect, pdf_doc, page_number, clip=pdf_page.rect)

        # Clear existing text objects to remove previous OCR text
        output_page.clean_contents(sanitize=True)  # Remove existing overlay text

        blocks = page.get("Blocks", [])
        for blocki, block in enumerate(blocks):
            if block["BlockType"] == "WORD":
                if verbose and blocki % 1000 == 0:
                    print(f"Processing block {blocki} on page {page_number + 1}")

                # Get the bbox object and scale it to the page pixel size
                bbox = BoundingBox.from_textract_bbox(block["Geometry"]["BoundingBox"])
                bbox.scale(output_page.rect.width, output_page.rect.height)

                rotation_angle = calculate_rotation(block["Geometry"]["Polygon"])
                # Add overlay text
                text = block["Text"]
                text_length = fitz.get_text_length(
                    text, fontname="helv", fontsize=12
                )
                fontsize_optimal = int(
                    math.floor((bbox.width / text_length) * 12)
                )

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

# Main section
doc = fitz.open("input.pdf")
data = json.load(open("response.json"))

print(f"Number of pages: {len(data)}")

num_word_blocks = sum(
    1 for page in data for blk in page.get("Blocks", []) if blk["BlockType"] == "WORD"
)
print(f"Number of WORD blocks: {num_word_blocks}")

selectable_pdf_doc = make_pdf_doc_searchable(
    pdf_doc=doc,
    textract_pages=data,
    add_word_bbox=True,
    show_selectable_char=False,
    pdf_image_dpi=100,
    verbose=True,
)

selectable_pdf_doc.save("output.pdf")