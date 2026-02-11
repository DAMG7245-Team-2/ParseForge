import os
import zipfile
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from backend.pipelines import (
    html_to_md_python,
    get_job_name,
    pdf_to_md_python,
    clean_temp_files,
    pdf_to_md_enterprise,
    html_to_md_enterprise,
)

from backend.logging_config import logger
from fastapi import Request

load_dotenv()
app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


class URLRequest(BaseModel):
    url: str


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}


@app.post("/processurl/", status_code=status.HTTP_200_OK)
async def process_url(
    background_tasks: BackgroundTasks,
    request: URLRequest,
    include_markdown: bool = Query(False),
    include_images: bool = Query(False),
    include_tables: bool = Query(False),
):
    logger.info(f"Processing URL: {request.url}")
    if not any([include_markdown, include_images, include_tables]):
        logger.error("At least one output type must be selected")
        raise HTTPException(
            status_code=400, detail="At least one output type must be selected"
        )
    try:
        url = request.url
        job_name = get_job_name()
        logger.info(f"Assigned job name: {job_name}")
        result = html_to_md_python(url, job_name)
        background_tasks.add_task(my_background_task)

        if include_images or include_tables:  # images or tables are requested
            flag, zip_buffer, messages = create_zip_archive(
                result, include_markdown, include_images, include_tables
            )
            if flag:
                logger.info("Returning zip archive")
                return StreamingResponse(
                    zip_buffer,
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={job_name}.zip"
                    },
                )
            else:
                logger.error(f"Failed to create zip archive: {messages}")
                raise HTTPException(status_code=500, detail=messages)
        else:
            if not result["markdown"]:
                logger.error("Markdown generation failed")
                raise HTTPException(
                    status_code=500,
                    detail="Markdown couldn't be generated. Maybe webpage has no data.",
                )
            logger.info("Returning markdown file")
            return FileResponse(
                result["markdown"],
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={job_name}.md"},
                filename=f"{job_name}.md",
            )

    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/processpdf/", status_code=status.HTTP_200_OK)
async def process_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    include_markdown: bool = Query(False),
    include_images: bool = Query(False),
    include_tables: bool = Query(False),
):
    logger.info(f"Processing PDF: {file.filename}")
    if not any([include_markdown, include_images, include_tables]):
        logger.error("At least one output type must be selected")
        raise HTTPException(
            status_code=400, detail="At least one output type must be selected"
        )

    if file.content_type != "application/pdf":
        logger.error(f"Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        background_tasks.add_task(my_background_task)
        contents = await file.read()
        output = Path("./temp_processing/output/pdf")
        os.makedirs(output, exist_ok=True)
        job_name = get_job_name()
        logger.info(f"Assigned job name: {job_name}")

        file_path = output / f"{job_name}.pdf"
        with open(file_path, "wb") as f:
            f.write(contents)
            await file.close()

        result = pdf_to_md_python(file_path, job_name)

        if include_images or include_tables:  # images or tables are requested
            flag, zip_buffer, messages = create_zip_archive(
                result, include_markdown, include_images, include_tables
            )
            if flag:
                logger.info("Returning zip archive")
                return StreamingResponse(
                    zip_buffer,
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={job_name}.zip"
                    },
                )
            else:
                logger.error(f"Failed to create zip archive: {messages}")
                raise HTTPException(status_code=500, detail=messages)

        else:
            if not result["markdown"] or not os.path.exists(result["markdown"]):
                logger.error("Markdown generation failed")
                raise HTTPException(
                    status_code=500,
                    detail="Markdown couldn't be generated. Maybe pdf has no data.",
                )
            logger.info("Returning markdown file")
            return FileResponse(
                result["markdown"],
                media_type="application/octet-stream",
                filename=f"{job_name}.md",
            )

    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()


@app.post("/processpdfenterprise/", status_code=status.HTTP_200_OK)
async def process_pdf_enterprise(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    include_markdown: bool = Query(False),
    include_images: bool = Query(False),
    include_tables: bool = Query(False),
):
    logger.info(f"Processing PDF (Enterprise): {file.filename}")
    if not any([include_markdown, include_images, include_tables]):
        logger.error("At least one output type must be selected")
        raise HTTPException(
            status_code=400, detail="At least one output type must be selected"
        )

    if file.content_type != "application/pdf":
        logger.error(f"Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be a PDF")
    try:
        background_tasks.add_task(my_background_task)
        contents = await file.read()
        output = Path("./temp_processing/output/pdf")
        os.makedirs(output, exist_ok=True)
        job_name = get_job_name()
        logger.info(f"Assigned job name: {job_name}")

        file_path = output / f"{job_name}.pdf"
        with open(file_path, "wb") as f:
            f.write(contents)
            await file.close()

        result = pdf_to_md_enterprise(file_path, job_name)

        if include_images or include_tables:  # images or tables are requested
            flag, zip_buffer, messages = create_zip_archive(
                result, include_markdown, include_images, include_tables
            )
            if flag:
                logger.info("Returning zip archive")
                return StreamingResponse(
                    zip_buffer,
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={job_name}.zip"
                    },
                )
            else:
                logger.error(f"Failed to create zip archive: {messages}")
                raise HTTPException(status_code=500, detail=messages)
        else:
            if not result["markdown"] or not os.path.exists(result["markdown"]):
                logger.error("Markdown generation failed")
                raise HTTPException(
                    status_code=500,
                    detail="Markdown couldn't be generated. Maybe webpage has no data.",
                )
            logger.info("Returning markdown file")
            return FileResponse(
                result["markdown"],
                media_type="application/octet-stream",
                filename=f"{job_name}.md",
            )

    except Exception as e:
        logger.error(f"Error processing PDF (Enterprise): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()


@app.post("/processurlenterprise/", status_code=status.HTTP_200_OK)
async def process_url_enterprise(
    background_tasks: BackgroundTasks,
    request: URLRequest,
    include_markdown: bool = Query(False),
    include_images: bool = Query(False),
    include_tables: bool = Query(False),
):
    logger.info(f"Processing URL (Enterprise): {request.url}")
    if not any([include_markdown, include_images, include_tables]):
        logger.error("At least one output type must be selected")
        raise HTTPException(
            status_code=400, detail="At least one output type must be selected"
        )
    try:
        url = request.url
        job_name = get_job_name()
        logger.info(f"Assigned job name: {job_name}")
        result = html_to_md_enterprise(url, job_name)
        background_tasks.add_task(my_background_task)

        if include_images or include_tables:  # images or tables are requested
            flag, zip_buffer, messages = create_zip_archive(
                result, include_markdown, include_images, include_tables
            )
            if flag:
                logger.info("Returning zip archive")
                return StreamingResponse(
                    zip_buffer,
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={job_name}.zip"
                    },
                )
            else:
                logger.error(f"Failed to create zip archive: {messages}")
                raise HTTPException(status_code=500, detail=messages)
        else:
            if not result["markdown"]:
                logger.error("Markdown generation failed")
                raise HTTPException(
                    status_code=500,
                    detail="Markdown couldn't be generated. Maybe webpage has no data.",
                )
            logger.info("Returning markdown file")
            return FileResponse(
                result["markdown"],
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={job_name}.md"},
                filename=f"{job_name}.md",
            )

    except Exception as e:
        logger.error(f"Error processing URL (Enterprise): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def create_zip_archive(result, include_markdown, include_images, include_tables):
    flag = False
    messages = []
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Markdown
        if include_markdown:
            if not result["markdown"]:
                messages.append(
                    "Markdown couldn't be generated. Maybe webpage has blockers."
                )
            else:
                zip_file.write(result["markdown"], arcname="document.md")
                flag = flag or True

        # Images
        if include_images:
            if not result["images"]:
                messages.append("No images found in the input webpage.")
            else:
                for img in result["images"].iterdir():
                    zip_file.write(img, arcname=f"images/{img.name}")
                flag = flag or True

        # Tables
        if include_tables:
            if not result["tables"]:
                messages.append("No tables found in the input webpage.")
            else:
                for table in result["tables"].iterdir():
                    zip_file.write(table, arcname=f"tables/{table.name}")
                flag = flag or True

    zip_buffer.seek(0)
    return flag, zip_buffer, messages


def my_background_task():
    clean_temp_files()
    print("Performed cleanup of temp files.")
