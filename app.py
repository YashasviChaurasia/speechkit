from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from speechkit.config import Settings
from speechkit.credentials import CredentialStore
from speechkit.exceptions import CredentialStoreError, MediaError, NoSpeechError, ProviderError, UnsupportedMediaError
from speechkit.fixture_provider import FixtureProvider
from speechkit.media import validate_upload_filename
from speechkit.sarvam_provider import SarvamProvider
from speechkit.service import SpeechService
from speechkit.storage import Storage


class PublicError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status, self.code, self.message, self.retryable = status, code, message, retryable


class Rename(BaseModel):
    display_name: str


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["speechkit"] = "speechkit"
    version: str


class ProviderConfiguration(BaseModel):
    provider: Literal["sarvam"] = "sarvam"
    configured: bool


class ProviderKey(BaseModel):
    api_key: str = Field(min_length=1, max_length=1024)


def public_error(error: PublicError) -> JSONResponse:
    return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": error.message, "retryable": error.retryable, "details": {}}})


def provider_error(error: ProviderError) -> PublicError:
    status = getattr(error, "status_code", None)
    if status == 403:
        return PublicError(502, "sarvam_authentication", "Sarvam authentication failed. Check the backend API key configuration.")
    if status == 429:
        return PublicError(503, "sarvam_rate_limited", "Sarvam is rate limiting transcription requests. Retry in a few minutes.", True)
    if status in {408, 504} or "timeout" in str(error).casefold():
        return PublicError(504, "provider_timeout", "Sarvam transcription timed out. Retry the recording.", True)
    if any(term in str(error).casefold() for term in ("invalid", "unreadable", "download", "artifact")):
        return PublicError(502, "provider_response_invalid", "Sarvam returned unusable transcription data. Retry the recording later.", True)
    return PublicError(502, "provider_error", "Sarvam could not produce a usable transcript. Retry in a few minutes.", True)


settings = Settings.from_env()
store = Storage(settings.data_dir / "speechlens.sqlite")
provider = FixtureProvider() if settings.fixture_mode else SarvamProvider(settings.api_key or "", poll_interval=settings.poll_interval, batch_timeout=settings.batch_timeout)
service = SpeechService(store, provider, settings.data_dir, settings.ffmpeg, settings.ffprobe, settings.fixture_mode)
credentials = CredentialStore()
app = FastAPI(title="SpeechLens", version="0.1.0")


@app.exception_handler(PublicError)
async def handle_public_error(_request: Request, error: PublicError):
    return public_error(error)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, _error: RequestValidationError):
    return public_error(PublicError(422, "invalid_request", "Request validation failed."))


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_request: Request, error: StarletteHTTPException):
    return public_error(PublicError(error.status_code, "not_found" if error.status_code == 404 else "http_error", "Resource not found." if error.status_code == 404 else "Request failed."))


@app.exception_handler(Exception)
async def handle_unexpected_error(_request: Request, error: Exception):
    if isinstance(error, sqlite3.Error):
        return public_error(PublicError(500, "storage_failure", "SpeechKit storage failed. Retry later."))
    return public_error(PublicError(500, "internal_error", "SpeechKit could not process the request. Retry later.", True))


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(version=app.version)


def provider_configuration() -> ProviderConfiguration:
    try:
        return ProviderConfiguration(configured=bool(credentials.get()))
    except CredentialStoreError:
        raise PublicError(500, "credential_store_unavailable", "SpeechKit could not access the operating-system credential store.")


@app.get("/api/provider/config", response_model=ProviderConfiguration)
def get_provider_config() -> ProviderConfiguration:
    return provider_configuration()


@app.put("/api/provider/config", response_model=ProviderConfiguration)
def put_provider_config(body: ProviderKey) -> ProviderConfiguration:
    api_key = body.api_key.strip()
    if not api_key:
        raise PublicError(422, "invalid_request", "Request validation failed.")
    try:
        credentials.save(api_key)
    except CredentialStoreError:
        raise PublicError(500, "credential_store_unavailable", "SpeechKit could not access the operating-system credential store.")
    return ProviderConfiguration(configured=True)


@app.delete("/api/provider/config", response_model=ProviderConfiguration)
def delete_provider_config() -> ProviderConfiguration:
    try:
        credentials.remove()
    except CredentialStoreError:
        raise PublicError(500, "credential_store_unavailable", "SpeechKit could not access the operating-system credential store.")
    return ProviderConfiguration(configured=False)


@app.post("/api/assets")
async def upload(file: UploadFile = File(...), num_speakers: int | None = Form(None, ge=1, le=20), mode: Literal["transcribe", "translate", "verbatim", "translit", "codemix"] = Form("transcribe")):
    if not file.filename:
        raise PublicError(400, "invalid_upload", "Choose an audio or video file.")
    try:
        filename = validate_upload_filename(file.filename)
    except UnsupportedMediaError:
        raise PublicError(415, "invalid_upload", "Choose a supported audio or video file.")
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            path = Path(tmp.name)
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise PublicError(413, "upload_too_large", "Upload exceeds the 500 MiB limit.")
                tmp.write(chunk)
        if size == 0:
            raise PublicError(400, "invalid_upload", "Upload is empty. Choose an audio or video file with spoken audio.")
        return {"asset_id": service.process(filename, path, num_speakers, mode), "stage": "complete"}
    except PublicError:
        raise
    except NoSpeechError:
        raise PublicError(422, "no_speech", "No clear spoken dialogue with usable timestamps was found.")
    except MediaError as error:
        message = str(error).casefold()
        if "no audio track" in message:
            raise PublicError(422, "media_no_audio", "The uploaded media has no audio track.")
        if "extract" in message or "empty audio track" in message:
            raise PublicError(422, "ffmpeg_failed", "SpeechKit could not extract usable audio from this file.")
        raise PublicError(422, "invalid_media", "SpeechKit could not read this media file.")
    except ProviderError as error:
        raise provider_error(error)
    finally:
        await file.close()
        if path and path.exists():
            path.unlink()


@app.get("/api/assets/{asset_id}")
def asset(asset_id: str):
    found = store.get_asset(asset_id)
    if not found:
        raise PublicError(404, "asset_not_found", "Asset not found.")
    return found


@app.get("/api/assets/{asset_id}/status")
def status(asset_id: str):
    return asset(asset_id)


@app.get("/api/assets/{asset_id}/artifact")
def artifact(asset_id: str):
    found = store.get_artifact(asset_id)
    if not found:
        raise PublicError(404, "artifact_not_found", "Completed artifact not found.")
    return found


@app.get("/api/assets/{asset_id}/media")
def media(asset_id: str):
    found = store.get_artifact_internal(asset_id)
    if not found:
        raise PublicError(404, "media_not_found", "Media not found.")
    return FileResponse(found["metadata"]["media_path"])


@app.get("/api/assets/{asset_id}/search")
def search(asset_id: str, q: str = Query(min_length=1), mode: Literal["smart", "phrase", "prefix", "substring", "closest"] = "smart"):
    started = time.perf_counter()
    results = store.search(asset_id, q, mode)
    return {"query": q, "mode": mode, "elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "results": results}


@app.patch("/api/assets/{asset_id}/speakers/{speaker_id}")
def rename(asset_id: str, speaker_id: str, body: Rename):
    try:
        store.rename_speaker(asset_id, speaker_id, body.display_name.strip())
        return {"ok": True}
    except KeyError:
        raise PublicError(404, "speaker_not_found", "Speaker not found.")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
