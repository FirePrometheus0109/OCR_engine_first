import boto3
import json
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

# Initialize the Textract client
textract_client = boto3.client("textract")

# Function to analyze a single page document
def analyze_document(page_bytes):
    print("Analyzing document...")
    response = textract_client.analyze_document(
        Document={"Bytes": page_bytes}, FeatureTypes=['TABLES', 'FORMS']
    )
    print("Analysis complete.")
    return response

# Function to process each page
def process_pdf(file_path):
    print(f"Opening PDF file: {file_path}")
    reader = PdfReader(file_path)
    num_pages = len(reader.pages)
    print(f"Number of pages to process: {num_pages}")
    responses = []

    for page_number in range(num_pages):
        print(f"Processing page {page_number + 1} of {num_pages}...")
        # Extract a single page
        writer = PdfWriter()
        writer.add_page(reader.pages[page_number])

        # Write the single page to a bytes object
        page_bytes_io = BytesIO()
        writer.write(page_bytes_io)
        page_bytes_io.seek(0)

        # Analyze the single page
        page_response = analyze_document(page_bytes_io.read())
        responses.append(page_response)

        print(f"Page {page_number + 1} processed.")

    print("All pages processed.")
    return responses

# Main function to process the document
def main():
    input_pdf_path = "input.pdf"
    print("Starting PDF processing...")

    # Process the PDF and get responses for each page
    responses = process_pdf(input_pdf_path)

    # Write the results to a JSON file
    output_json_path = "response.json"
    with open(output_json_path, "w") as output_file:
        json.dump(responses, output_file)

    print(f"Responses written to {output_json_path}.")
    print("Processing complete.")

if __name__ == "__main__":
    main()