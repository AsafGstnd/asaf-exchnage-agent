from utils.pdf_processor import extract_markdown_from_pdf

if __name__ == "__main__":
    pdf_path = "data/sample.pdf"  # Change this to your PDF file name if needed

    md_text = extract_markdown_from_pdf(pdf_path)
    print("\nExtracted Markdown:\n")
    print(md_text)
