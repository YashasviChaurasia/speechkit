from __future__ import annotations
import tempfile, time
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from speechkit.config import Settings
from speechkit.sarvam_provider import SarvamProvider
from speechkit.service import SpeechService
from speechkit.storage import Storage
from speechkit.exceptions import MediaError, NoSpeechError, ProviderError, UnsupportedMediaError
from speechkit.media import validate_upload_filename

settings=Settings.from_env(); store=Storage(settings.data_dir/"speechlens.sqlite")
service=SpeechService(store,SarvamProvider(settings.api_key,poll_interval=settings.poll_interval,batch_timeout=settings.batch_timeout),settings.data_dir,settings.ffmpeg,settings.ffprobe)
app=FastAPI(title="SpeechLens")

class Rename(BaseModel): display_name: str

def provider_failure(error: ProviderError) -> tuple[int, str]:
    message = str(error).casefold()
    if "invalid json" in message or "invalid transcript payload" in message or "invalid file results" in message:
        return 502, "Sarvam returned an unreadable transcript response. The recording was marked failed; retry in a few minutes."
    if "without successful files" in message:
        return 422, "Sarvam could not transcribe this file. Confirm it contains clear spoken audio, then retry."
    if "could not complete" in message or "request failed" in message:
        return 503, "Sarvam could not complete the Batch transcription. The recording was marked failed; retry in a few minutes."
    if "could not download" in message:
        return 502, "Sarvam completed the job but the transcript could not be downloaded. Retry in a few minutes."
    return 502, "Sarvam could not produce a usable transcript. The recording was marked failed; retry in a few minutes."

@app.post("/api/assets")
async def upload(file: UploadFile=File(...), num_speakers:int|None=Form(None,ge=1,le=20)):
    if not file.filename: raise HTTPException(400,"Choose an audio or video file.")
    try: filename=validate_upload_filename(file.filename)
    except UnsupportedMediaError as error: raise HTTPException(415,str(error)) from error
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False,suffix=Path(filename).suffix) as tmp:
            path=Path(tmp.name); size=0
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>settings.max_upload_bytes: raise HTTPException(413,"Upload exceeds configured maximum size.")
                tmp.write(chunk)
        if size == 0: raise HTTPException(400,"Upload is empty. Choose an audio or video file with spoken audio.")
        return {"asset_id":service.process(filename,path,num_speakers),"stage":"complete"}
    except HTTPException: raise
    except NoSpeechError as error: raise HTTPException(422,str(error)) from error
    except MediaError as error: raise HTTPException(422,str(error)) from error
    except ProviderError as error:
        status, detail = provider_failure(error)
        raise HTTPException(status,detail) from error
    except Exception as error: raise HTTPException(500,"Processing failed unexpectedly. The asset was marked failed; retry the recording.") from error
    finally:
        await file.close()
        if path and path.exists():
            path.unlink()
@app.get("/api/assets/{asset_id}")
def asset(asset_id:str):
    found=store.get_asset(asset_id)
    if not found: raise HTTPException(404,"Asset not found")
    return found
@app.get("/api/assets/{asset_id}/status")
def status(asset_id:str): return asset(asset_id)
@app.get("/api/assets/{asset_id}/artifact")
def artifact(asset_id:str):
    found=store.get_artifact(asset_id)
    if not found: raise HTTPException(404,"Completed artifact not found")
    return found
@app.get("/api/assets/{asset_id}/media")
def media(asset_id:str):
    found=store.get_artifact(asset_id)
    if not found: raise HTTPException(404,"Media not found")
    return FileResponse(found["metadata"]["media_path"])
@app.get("/api/assets/{asset_id}/search")
def search(asset_id:str, q:str=Query(min_length=1), mode:Literal["smart", "phrase", "prefix", "substring", "closest"]="smart"):
    started=time.perf_counter(); results=store.search(asset_id,q,mode)
    return {"query":q,"mode":mode,"elapsed_ms":round((time.perf_counter()-started)*1000,3),"results":results}
@app.patch("/api/assets/{asset_id}/speakers/{speaker_id}")
def rename(asset_id:str,speaker_id:str,body:Rename):
    try: store.rename_speaker(asset_id,speaker_id,body.display_name.strip()); return {"ok":True}
    except KeyError: raise HTTPException(404,"Speaker not found")

app.mount("/",StaticFiles(directory="static",html=True),name="static")
