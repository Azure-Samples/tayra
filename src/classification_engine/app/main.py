"""FastAPI surface for triggering and querying call classifications."""

from typing import Optional
from urllib.parse import unquote

from dotenv import find_dotenv, load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from . import __app__, __version__
from .background import run_classification_job
from .database import ClassificationDatabase
from .schemas import BodyMessage, ClassificationJobParams, RESPONSES


load_dotenv(find_dotenv())


tags_metadata: list[dict] = [
    {
        "name": "Background Tasks",
        "description": "Endpoints used to kick off asynchronous classification jobs.",
    },
    {
        "name": "Operational Tasks",
        "description": "Endpoints for reading transcription and classification data.",
    },
]

description = (
    "Web API to trigger call intent classification jobs and inspect results stored inside"
    " Cosmos DB."
)


app: FastAPI = FastAPI(
    title=__app__,
    version=__version__,
    description=description,
    openapi_tags=tags_metadata,
    openapi_url="/api/v1/openapi.json",
    responses=RESPONSES,  # type: ignore
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


database = ClassificationDatabase()


@app.get("/", response_class=HTMLResponse, tags=["Operational Tasks"])
async def index() -> HTMLResponse:
        html = """
        <!doctype html>
        <html lang=\"en\">
            <head>
                <meta charset=\"utf-8\">
                <title>Tayra Classification Engine</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; }
                    h1 { color: #0b5fff; }
                    ul { line-height: 1.8; }
                    a { color: #0b5fff; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <h1>Tayra Classification Engine</h1>
                <p>Select an action:</p>
                <ul>
                    <li><strong>POST</strong> <code>/classification</code> &mdash; trigger a background classification job.</li>
                    <li><a href=\"/transcriptions\">GET /transcriptions</a> &mdash; list manager documents.</li>
                    <li><a href=\"/transcription-by-file?file_name=example.mp3\">GET /transcription-by-file</a> &mdash; fetch a transcription by filename.</li>
                    <li><a href=\"/classification-records\">GET /classification-records</a> &mdash; view stored classification records.</li>
                    <li><a href=\"/docs\">OpenAPI docs</a> &mdash; interactive API explorer.</li>
                </ul>
            </body>
        </html>
        """
        return HTMLResponse(content=html)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    response_body = BodyMessage(
        success=False,
        type="Validation Error",
        title="Your request parameters did not validate.",
        detail={"invalid-params": list(exc.errors())},
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(response_body),
    )


@app.post("/classification", tags=["Background Tasks"])
async def classify_calls(
    background_tasks: BackgroundTasks, params: ClassificationJobParams
) -> JSONResponse:
    background_tasks.add_task(run_classification_job, params)
    return JSONResponse({"result": "Classification job accepted."})


@app.get("/transcriptions", tags=["Operational Tasks"])
async def get_transcriptions() -> JSONResponse:
    data = await database.load_transcriptions()
    return JSONResponse({"result": data})


@app.get("/transcription-by-file", tags=["Operational Tasks"])
async def get_transcription_by_file(file_name: str) -> JSONResponse:
    decoded_file = unquote(file_name)
    data = await database.load_transcription_by_filename(decoded_file)
    if not data:
        return JSONResponse(
            {"result": None, "message": "Transcription not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return JSONResponse({"result": data})



@app.get("/classification-records", tags=["Operational Tasks"])
async def get_classification_records(
    manager: Optional[str] = None, specialist: Optional[str] = None
) -> JSONResponse:
    decoded_manager = unquote(manager) if manager else None
    decoded_specialist = unquote(specialist) if specialist else None
    data = await database.load_classification_records(
        manager=decoded_manager,
        specialist=decoded_specialist,
    )
    return JSONResponse({"result": data})


@app.get("/classification-other", tags=["Operational Tasks"])
async def get_top_other_classifications(limit: int = 3, order_type: str = "other") -> JSONResponse:
    safe_limit = max(1, limit)
    data = await database.load_top_other_classifications(safe_limit, order_type)
    return JSONResponse({"result": data})
