from utils.pdf_processor import extract_markdown_from_pdf

if __name__ == "__main__":
    pdf_path = "data/external_universities/romania/alexandru_ioan_cuza_university_of_iasi/factsheet.pdf"

    md_text = extract_markdown_from_pdf(pdf_path)
    print("\nExtracted Markdown from:", pdf_path)
    print(md_text)
