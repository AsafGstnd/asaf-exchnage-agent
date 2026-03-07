from utils.pdf_processor import extract_text_from_pdf

if __name__ == "__main__":
    pdf_path_tub = "data/external_universities/germany/technical_university_of_berlin_tub/factsheet.pdf"
    pdf_path_alexandro = "data/external_universities/romania/alexandru_ioan_cuza_university_of_iasi/factsheet.pdf"

    md_text = extract_text_from_pdf(pdf_path_tub)
    print("\nExtracted Text from:", pdf_path_tub)
    print(md_text)
