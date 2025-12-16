import os
import re

import requests
import streamlit as st
from dotenv import load_dotenv

# --- 1. Configuration and Initialization ---
load_dotenv()
FASTAPI_URL = os.getenv("FASTAPI_URL", "https://nehadevarapalli-parseforge.hf.space")
APP_NAME = "ParseForge"
APP_DESCRIPTION = """📄🌐 A versatile document processing tool that converts PDFs and webpages into structured markdown content and extracts all data. 
Choose between our **custom Python parser** (built with PyMuPDF, Docling, and BeautifulSoup) or the **enterprise-grade Llama parser (for PDFs) or Firecrawl (for Webpages)** for comparison."""

st.set_page_config(page_title=APP_NAME, page_icon="⚙️", layout="centered")

if "input_type" not in st.session_state:
    st.session_state.input_type = "PDF"

if "backend_healthy" not in st.session_state:
    st.session_state["backend_healthy"] = None


# --- 2. Backend Health Check Function ---
def check_backend_health():
    """Checks the health of the FastAPI backend using a dedicated /health endpoint."""
    try:
        # We assume the FastAPI backend exposes a /health endpoint
        response = requests.get(f"{FASTAPI_URL}/health", timeout=5)

        # Check if the status code indicates success (typically 200)
        if response.status_code == 200:
            return True
        else:
            return False

    except requests.exceptions.RequestException as e:
        # Handles connection errors, timeouts, and DNS failures
        print(f"Health check failed: {e}")
        return False


# --- 3. App Header and Health Display ---
st.title(f"⚙️ {APP_NAME}")

# Run the health check only if the status hasn't been determined yet
if st.session_state["backend_healthy"] is None:
    st.session_state["backend_healthy"] = check_backend_health()

# Display Health Status
health_status = st.session_state["backend_healthy"]
status_col, desc_col = st.columns([1, 4])

with status_col:
    if health_status:
        st.markdown(
            "**Backend Status:** <span style='color:green; font-weight:bold;'>🟢 Online</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "**Backend Status:** <span style='color:red; font-weight:bold;'>🔴 Offline</span>",
            unsafe_allow_html=True,
        )

with desc_col:
    st.markdown(f"*{APP_DESCRIPTION}*")

st.divider()

# Input Type Selector
input_col, parser_col = st.columns([1, 1])
with input_col:
    input_type = st.radio(
        "Select Input Type", ["📄 PDF File", "🌐 Webpage URL"], horizontal=True
    )

parser_options = ["Python Parser", "Standardize Docling", "Standardize MarkItDown"]
if "PDF" in input_type:
    parser_options.append("Llama Parser")
else:
    parser_options.append("Firecrawl")

with parser_col:
    parser_type = st.selectbox(
        "Choose Parser Engine:",
        parser_options,
        index=0,  # Default selection
        format_func=lambda x: "Select Parser" if x == "" else x,
        help="""Python Parser: Custom-built using PyMuPDF (image extraction), Docling (text & table extraction), 
BeautifulSoup (webpage parsing). Optimized for specific use cases.\nLlama Parser: AI-powered enterprise solution for superior accuracy (use for PDFs).\n 
Firecrawl: Advanced web scraping and parsing engine (use for webpages).\nStandardize Docling: Standardize document using Docling.\nStandardize MarkItDown: Standardize document using MarkItDown.""",
        disabled=False,
    )

# File/URL Input Section
if "PDF" in input_type:
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        help="Maximum file size: 10MB. Extracts text, tables, and images.",
    )
else:
    url_input = st.text_input(
        "Enter Webpage URL: ",
        placeholder="https://example.com",
        help="Paste a webpage URL to process. Extracts text, tables, and images.",
    )

st.divider()

# Output options
if parser_type not in ["Standardize Docling", "Standardize MarkItDown"]:
    st.subheader("🔧 Output Options")
    output_col = st.columns([1])[0]

    with output_col:
        output_formats = st.multiselect(
            "Select components to include:",
            options=["Markdown", "Images", "Tables"],
            default=["Markdown"],
            help="Choose which components to include in your output.",
        )

    # Disable processing if the backend is offline OR input/outputs are missing
    process_disabled = (
        (not health_status)
        or len(output_formats) == 0
        or ("PDF" in input_type and not uploaded_file)
        or ("Webpage" in input_type and not url_input)
    )

    if process_disabled and not health_status:
        st.error("Processing disabled because the backend service is offline.")
    elif process_disabled and len(output_formats) == 0:
        st.caption(
            "ℹ️ Please select at least one output component to enable processing."
        )
    elif process_disabled and (
        "PDF" in input_type
        and not uploaded_file
        or "Webpage" in input_type
        and not url_input
    ):
        st.caption("ℹ️ Please provide a valid input to enable processing.")
else:
    # Standardization options don't require output formats selection
    process_disabled = (
        (not health_status)
        or ("PDF" in input_type and not uploaded_file)
        or ("Webpage" in input_type and not url_input)
    )
    if process_disabled and not health_status:
        st.error("Processing disabled because the backend service is offline.")


def process_content(endpoint, files=None, json=None, params=None, timeout=300):
    try:
        response = requests.post(
            f"{FASTAPI_URL}{endpoint}", 
            files=files, 
            json=json, 
            params=params, 
            timeout=timeout,
        )
        # Raise for HTTP errors
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        st.error(
            "❌ Connection error: Could not connect to the backend service."
            "Please try again in a few minutes."
        )
        # Logging tech detail for debugging
        st.caption(f"❌ Connection error detail: {e}")
        return
    except requests.exceptions.Timeout as e:
        st.error(
            f"❌ Timeout error: The request took longer than {timeout} seconds to complete."
            "Please try again."
        )
        return
    except requests.exceptions.HTTPError as e:
        # Backend returned 4xx/5xx with a body
        status = e.response.status_code if e.response is not None else "unknown"
        text = e.response.text if e.response is not None else ""
        st.error(f"❌ HTTP error: {status} - {text}")
        return
    except requests.exceptions.RequestException as e:
        # Catch-all for other request errors
        st.error(f"❌ Unexpected error while calling the backend: {e}")
        return
    
    # Success path (200 OK)
    content_disposition = response.headers.get("Content-Disposition", "")
    match = re.findall(r'filename="?([^"]+)"?', content_disposition)
    filename = match[0] if match else "downloaded_file"
    if filename.endswith(".zip"):
        st.success("✅ All components processed successfully!")
        st.download_button(
            label="⬇️ Download ZIP Archive",
            data=response.content,
            file_name=filename,
            mime="application/zip",
        )
    else:
        st.success("✅ Markdown processed successfully!")
        st.download_button(
            label="⬇️ Download Markdown",
            data=response.content,
            file_name=filename,
            mime="text/markdown",
        )


# Process Button
if st.button(
    "✨ Process Content",
    type="primary",
    use_container_width=True,
    disabled=process_disabled,
):
    if parser_type in ["Standardize Docling", "Standardize MarkItDown"]:
        if "PDF" in input_type and uploaded_file:
            endpoint = (
                "/standardizedoclingpdf/"
                if parser_type == "Standardize Docling"
                else "/standardizemarkitdownpdf/"
            )
            with st.spinner("🔍 Standardizing PDF content..."):
                process_content(
                    endpoint,
                    files={
                        "file": (uploaded_file.name, uploaded_file, "application/pdf")
                    },
                )
        elif "Webpage" in input_type and url_input:
            endpoint = (
                "/standardizedoclingurl/"
                if parser_type == "Standardize Docling"
                else "/standardizemarkitdownurl/"
            )
            with st.spinner("🌐 Standardizing webpage content..."):
                process_content(endpoint, json={"url": url_input})
    else:
        params = {
            "include_markdown": "Markdown" in output_formats,
            "include_images": "Images" in output_formats,
            "include_tables": "Tables" in output_formats,
        }

        if parser_type == "Llama Parser":
            with st.spinner("🔍 Parsing PDF content with Llama Parser..."):
                process_content(
                    "/processpdfenterprise/",
                    files={
                        "file": (uploaded_file.name, uploaded_file, "application/pdf")
                    },
                    params=params,
                )
        elif parser_type == "Firecrawl":
            with st.spinner("🌐 Parsing webpage content with Firecrawl..."):
                process_content(
                    "/processurlenterprise/", json={"url": url_input}, params=params
                )
        else:
            if "PDF" in input_type and uploaded_file:
                with st.spinner("🔍 Parsing PDF content..."):
                    process_content(
                        "/processpdf/",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file,
                                "application/pdf",
                            )
                        },
                        params=params,
                    )
            else:
                with st.spinner("🌐 Analyzing webpage content..."):
                    process_content(
                        "/processurl/", json={"url": url_input}, params=params
                    )

# Feature Explanation
with st.expander("ℹ️ About ParseForge Features"):
    st.markdown(
        """
    **Key Features:**
    - **Custom Python Parser** *(Default Option)*:
        - **PDF Parsing:** 
            - Built using PyMuPDF for extracting images from PDFs.
            - Uses Docling to extract text and tables with precision.
        - **Webpage Parsing:** 
            - Powered by BeautifulSoup for extracting structured content from webpages.
            - Suitable for projects requiring lightweight, rule-based parsing.
    - **Llama Parser** *(Enterprise PDF Parsing)*:
        - AI-powered solution offering superior accuracy for complex layouts.
        - Ideal for enterprise use cases where advanced document understanding is required.
    - **Firecrawl** *(Enterprise Webpage Parsing)*:
        - Advanced web scraping engine for extracting structured content from webpages.
        - Suitable for projects requiring advanced web scraping capabilities.
    - **Standardization Options:**
        - **Standardize Docling:** 
            - Standardize document structure using Docling.
        - **Standardize MarkItDown:** 
            - Standardize document structure using MarkItDown.
    - **Multi-Format Support:**
        - PDF documents (scanned & digital)
        - Webpages (articles, blogs, documentation)
    - **Output Options:**
        - Clean Markdown formatting
        - Preserved document structure
    """
    )
