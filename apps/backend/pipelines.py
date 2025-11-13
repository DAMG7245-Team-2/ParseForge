import os
import shutil
import uuid
from pathlib import Path

import requests
from docling.document_converter import DocumentConverter
from markitdown import MarkItDown

from cloud_ops import upload_file_to_s3, upload_directory_to_s3
from firecrawl_code import firecrawl
from llamaparser_pdf import llama_parse_pdf
from python_pdf_extraction import extract_text_with_docling, extract_images_to_folder, extract_tables_with_docling
from webscraper import WebScraper

base_dir = Path('./temp_processing')
output = base_dir / Path('output')
s3_bucket = 'neu-pdf-webpage-parser'
s3_pdf_input_prefix = 'pdfs/raw'
s3_html_input_prefix = 'html/raw'


def html_to_md_docling(url: str, job_name: uuid):
    s3_prefix_text = 'html/html-parser/extracted-text'
    s3_prefix_images = 'html/html-parser/extracted-images'
    s3_prefix_tables = 'html/html-parser/extracted-tables'

    output_data = {
        'markdown': None,
        'images': None,
        'tables': None
    }

    # Step 1: Extract images & tables
    out = WebScraper(url, job_name).extract_all()
    html_path = output / 'html' / f'{job_name}.html'

    # Step 2: Upload input HTML to S3
    input_html_s3_key = f'{s3_html_input_prefix}/{job_name}.html'
    upload_file_to_s3(str(html_path), input_html_s3_key, bucket_name=s3_bucket)

    # Step 3: Upload images and tables to S3
    images_local_folder = output / "extracted_images"
    tables_local_folder = output / "extracted_tables"

    if images_local_folder.exists() and any(images_local_folder.iterdir()):
        output_data['images'] = images_local_folder
        upload_directory_to_s3(str(images_local_folder), s3_prefix_images, bucket_name=s3_bucket)

    if tables_local_folder.exists() and any(tables_local_folder.iterdir()):
        output_data['tables'] = tables_local_folder
        upload_directory_to_s3(str(tables_local_folder), s3_prefix_tables, bucket_name=s3_bucket)

    # Step 4: Extract text and upload Markdown file to S3
    doc_converter = DocumentConverter()
    conv_result = doc_converter.convert(output / 'html' / f'{job_name}.html')
    markdown_output = conv_result.document.export_to_markdown()
    os.makedirs(output / 'markdown', exist_ok=True)
    markdown_path = output / 'markdown' / f'{job_name}.md'
    with open(markdown_path, 'w') as f:
        f.write(markdown_output)

    if markdown_path.exists() and not is_file_empty(markdown_path):
        output_data['markdown'] = markdown_path
        markdown_s3_key = f'{s3_prefix_text}/{job_name}.md'
        upload_file_to_s3(str(markdown_path), markdown_s3_key, bucket_name=s3_bucket)

    return output_data


def html_to_md_markitdown(url: str, job_name: uuid):
    s3_prefix_text = 'html/html-parser/extracted-text'
    s3_prefix_images = 'html/html-parser/extracted-images'
    s3_prefix_tables = 'html/html-parser/extracted-tables'

    output_data = {
        'markdown': None,
        'images': None,
        'tables': None
    }

    # Step 1: Extract images & tables
    out = WebScraper(url, job_name).extract_all()
    html_path = output / 'html' / f'{job_name}.html'

    # Step 2: Upload input HTML to S3
    input_html_s3_key = f'{s3_html_input_prefix}/{job_name}.html'
    upload_file_to_s3(str(html_path), input_html_s3_key, bucket_name=s3_bucket)

    # Step 3: Upload images and tables to S3
    images_local_folder = output / "extracted_images"
    tables_local_folder = output / "extracted_tables"
    if images_local_folder.exists() and any(images_local_folder.iterdir()):
        output_data['images'] = images_local_folder
        upload_directory_to_s3(str(images_local_folder), s3_prefix_images, bucket_name=s3_bucket)

    if tables_local_folder.exists() and any(tables_local_folder.iterdir()):
        output_data['tables'] = tables_local_folder
        upload_directory_to_s3(str(tables_local_folder), s3_prefix_tables, bucket_name=s3_bucket)

    # Step 4: Extract text and upload Markdown file to S3
    md = MarkItDown()
    markdown_output = md.convert(str(output / 'html' / f'{job_name}.html'))
    os.makedirs(output / 'markdown', exist_ok=True)
    markdown_path = output / 'markdown' / f'{job_name}.md'
    with open(markdown_path, 'w') as f:
        f.write(markdown_output.text_content)

    if markdown_path.exists() and not is_file_empty(markdown_path):
        output_data['markdown'] = markdown_path
        markdown_s3_key = f'{s3_prefix_text}/{job_name}.md'
        upload_file_to_s3(str(markdown_path), markdown_s3_key, bucket_name=s3_bucket)

    return output_data


def standardize_docling(input: str, job_name: uuid):
    if input.startswith("http://") or input.startswith("https://"):
        s3_prefix_text = 'html/docling/extracted-text'
        try:
            html_data = WebScraper(input, job_name).get_webpage()
            file = output / 'html' / f'{job_name}.html'
            os.makedirs(output / 'html', exist_ok=True)
            with open(file, 'w') as f:
                f.write(html_data)
            html_cloud_path = f'{s3_html_input_prefix}/{job_name}.html'
            upload_file_to_s3(str(file), html_cloud_path, bucket_name=s3_bucket)
        except Exception as e:
            print(e)
            return -1
    else:
        file = Path(input)
        if file.suffix != '.pdf':
            raise ValueError("Input file must be a PDF")
        s3_prefix_text = 'pdfs/docling/extracted-text'
        pdf_cloud_path = f'{s3_pdf_input_prefix}/{job_name}.pdf'
        upload_file_to_s3(str(file), pdf_cloud_path, bucket_name=s3_bucket)

    doc_converter = DocumentConverter()
    conv_result = doc_converter.convert(str(file))
    markdown_output = conv_result.document.export_to_markdown()

    markdown_dir = output / 'markdown'
    os.makedirs(markdown_dir, exist_ok=True)
    markdown_path = markdown_dir / f'{job_name}.md'
    with open(markdown_path, 'w') as f:
        f.write(markdown_output)

    # Upload MD to S3
    markdown_s3_key = f'{s3_prefix_text}/{job_name}.md'
    upload_file_to_s3(str(markdown_path), markdown_s3_key, bucket_name=s3_bucket)

    return markdown_path


def standardize_markitdown(input: str, job_name: uuid):
    if input.startswith("http://") or input.startswith("https://"):
        s3_prefix_text = 'html/markitdown/extracted-text'
        try:
            html_data = WebScraper(input, job_name).get_webpage()
            file = output / 'html' / f'{job_name}.html'
            os.makedirs(output / 'html', exist_ok=True)
            with open(file, 'w') as f:
                f.write(html_data)
            html_cloud_path = f'{s3_html_input_prefix}/{job_name}.html'
            upload_file_to_s3(str(file), html_cloud_path, bucket_name=s3_bucket)
        except Exception as e:
            print(e)
            return -1
    else:
        file = Path(input)
        if file.suffix != '.pdf':
            raise ValueError("Input file must be a PDF")
        s3_prefix_text = 'pdfs/markitdown/extracted-text'
        pdf_cloud_path = f'{s3_pdf_input_prefix}/{job_name}.pdf'
        upload_file_to_s3(str(file), pdf_cloud_path, bucket_name=s3_bucket)
        
    md = MarkItDown()
    conv_result = md.convert(str(file))

    markdown_dir = output / 'markdown'
    os.makedirs(markdown_dir, exist_ok=True)
    markdown_path = markdown_dir / f'{job_name}.md'
    with open(markdown_path, 'w') as f:
        f.write(conv_result.text_content)

    # Upload MD to S3
    markdown_s3_key = f'{s3_prefix_text}/{job_name}.md'
    upload_file_to_s3(str(markdown_path), markdown_s3_key, bucket_name=s3_bucket)

    return markdown_path


def pdf_to_md_docling(file: Path, job_name: uuid):
    s3_prefix_text = 'pdfs/python-parser/extracted-text'
    s3_prefix_images = 'pdfs/python-parser/extracted-images'
    s3_prefix_tables = 'pdfs/python-parser/extracted-tables'

    output_data = {
        'markdown': None,
        'images': None,
        'tables': None
    }

    # Step 1: Upload input PDF to S3
    input_pdf_s3_key = f'{s3_pdf_input_prefix}/{job_name}.pdf'
    upload_file_to_s3(str(file), input_pdf_s3_key, bucket_name=s3_bucket)

    # Step 2: Extract text and upload Markdown file to S3
    markdown_local_path = output / f'{job_name}.md'
    extract_text_with_docling(file, markdown_local_path)

    if markdown_local_path.exists() and not is_file_empty(markdown_local_path):
        output_data['markdown'] = markdown_local_path
        markdown_s3_key = f'{s3_prefix_text}/{Path(markdown_local_path).name}'
        upload_file_to_s3(str(markdown_local_path), markdown_s3_key, bucket_name=s3_bucket)

    # Step 3: Extract images and upload the directory to S3
    images_local_folder = output / "extracted_images"
    extract_images_to_folder(file, images_local_folder)

    if images_local_folder.exists() and any(images_local_folder.iterdir()):
        output_data['images'] = images_local_folder
        upload_directory_to_s3(str(images_local_folder), s3_prefix_images, bucket_name=s3_bucket)

    # Step 4: Extract tables and upload the directory to S3
    tables_local_folder = output / "extracted_tables"
    extract_tables_with_docling(file, tables_local_folder)

    if tables_local_folder.exists() and any(tables_local_folder.iterdir()):
        output_data['tables'] = tables_local_folder
        upload_directory_to_s3(str(tables_local_folder), s3_prefix_tables, bucket_name=s3_bucket)

    return output_data


def pdf_to_md_enterprise(file: Path, job_name: uuid):
    s3_prefix_text = 'pdfs/llama-parser/extracted-text'
    s3_prefix_images = 'pdfs/llama-parser/extracted-images'
    s3_prefix_tables = 'pdfs/llama-parser/extracted-tables'

    output_data = {
        'markdown': None,
        'images': None,
        'tables': None
    }

    markdown_path = llama_parse_pdf(str(file), job_name)
    images_local_folder = output / "extracted_images"
    tables_local_folder = output / "extracted_tables"

    # Step 1: Upload input PDF to S3
    input_pdf_s3_key = f'{s3_pdf_input_prefix}/{job_name}.pdf'
    upload_file_to_s3(str(file), input_pdf_s3_key, bucket_name=s3_bucket)

    # Step 2: Upload images and tables to S3
    if images_local_folder.exists() and any(images_local_folder.iterdir()):
        output_data['images'] = images_local_folder
        upload_directory_to_s3(str(images_local_folder), s3_prefix_images, bucket_name=s3_bucket)

    if tables_local_folder.exists() and any(tables_local_folder.iterdir()):
        output_data['tables'] = tables_local_folder
        upload_directory_to_s3(str(tables_local_folder), s3_prefix_tables, bucket_name=s3_bucket)

    # Step 3: Upload Markdown to S3
    if markdown_path.exists() and not is_file_empty(markdown_path):
        output_data['markdown'] = markdown_path
        markdown_s3_key = f'{s3_prefix_text}/{job_name}.md'
        upload_file_to_s3(str(markdown_path), markdown_s3_key, bucket_name=s3_bucket)

    return output_data


def html_to_md_enterprise(url: str, job_name: uuid):
    s3_prefix_text = 'html/firecrawl/extracted-text'
    s3_prefix_images = 'html/firecrawl/extracted-images'
    s3_prefix_tables = 'html/firecrawl/extracted-tables'

    output_data = {
        'markdown': None,
        'images': None,
        'tables': None
    }

    html_path = output / f'{job_name}.html'
    images_local_folder = output / "extracted_images"
    tables_local_folder = output / "extracted_tables"
    markdown_path = output / 'markdown' / f'{job_name}.md'

    firecrawl(url, job_name)

    response = requests.get(url)
    with open(html_path, 'wb') as f:
        f.write(response.content)

    input_html_s3_key = f'{s3_html_input_prefix}/{job_name}.html'
    upload_file_to_s3(str(html_path), input_html_s3_key, bucket_name=s3_bucket)
    if images_local_folder.exists() and any(images_local_folder.iterdir()):
        output_data['images'] = images_local_folder
        upload_directory_to_s3(str(images_local_folder), s3_prefix_images, bucket_name=s3_bucket)

    if tables_local_folder.exists() and any(tables_local_folder.iterdir()):
        output_data['tables'] = tables_local_folder
        upload_directory_to_s3(str(tables_local_folder), s3_prefix_tables, bucket_name=s3_bucket)

    if markdown_path.exists() and not is_file_empty(markdown_path):
        output_data['markdown'] = markdown_path
        markdown_s3_key = f'{s3_prefix_text}/{job_name}.md'
        upload_file_to_s3(str(markdown_path), markdown_s3_key, bucket_name=s3_bucket)

    return output_data

def is_file_empty(file_path: Path) -> bool:
    return file_path.stat().st_size == 0

def get_job_name():
    return uuid.uuid4()


def clean_temp_files():
    shutil.rmtree(base_dir, ignore_errors=True)
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(output, exist_ok=True)
