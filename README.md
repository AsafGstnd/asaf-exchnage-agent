
# Fez Exchange Agent

## Project Description
Fez Exchange Agent is a toolkit for extracting, processing, and analyzing university requirements and documents using generative AI and data science techniques. It supports PDF parsing, text chunking, and requirements extraction for academic exchange programs.

## Features
- PDF extraction and processing
- Requirements extraction from university documents
- RAG (Retrieval-Augmented Generation) embedding pipeline
- Utilities for database and configuration management
- Test scripts for validation

## Quick Setup

1. Create a virtual environment:
    python -m venv venv

2. Activate the virtual environment:
    - Windows:
      venv\Scripts\activate
    - macOS/Linux:
      source venv/bin/activate

3. Install requirements:
    pip install -r requirements.txt

4. Run tests:
    python -m tests.test_text_splitter
    python -m tests.test_req_extraction

## Folder Structure
- data/: University documents and samples
- data_pipeline/: Extraction and embedding scripts
- orchestration/: Specialist modules
- utils/: Utilities for PDF, DB, and config
- tests/: Test scripts

---
For more details, see the code and requirements.txt.