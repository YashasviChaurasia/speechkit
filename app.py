from __future__ import annotations
import shutil, tempfile
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from speechkit.config import Settings
from speechkit.sarvam_provider import SarvamProvider
from speechkit.service import SpeechService
from speechkit.storage import Storage

settings=Settings.from_env(); store=Storage(settings.data_dir/"speechlens.sqlite")
service=SpeechService(store,SarvamProvider(settings.api_key,poll_interval=settings.poll_interval,batch_timeout=settings.batch_timeout),settings.data_dir,settings.ffmpeg,settings.ffprobe)
app=FastAPI(title="SpeechLens")

class Rename(BaseModel): display_name: str
@app.post("/api/assets")
async def upload(file: UploadFile=File(...), num_speakers:int|None=None):
    if not file.filename: raise HTTPException(400,"Choose an audio or video file.")
    with tempfile.NamedTemporaryFile(delete=False,suffix=Path(file.filename).suffix) as tmp: shutil.copyfileobj(file.file,tmp); path=Path(tmp.name)
    if path.stat().st_size>settings.max_upload_bytes: path.unlink(); raise HTTPException(413,"Upload exceeds configured maximum size.")
    try: return {"asset_id":service.process(file.filename,path,num_speakers),"stage":"complete"}
    except Exception as e: raise HTTPException(422,str(e)) from e
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
def search(asset_id:str,q:str=Query(min_length=1)): return {"query":q,"results":store.search(asset_id,q)}
@app.patch("/api/assets/{asset_id}/speakers/{speaker_id}")
def rename(asset_id:str,speaker_id:str,body:Rename):
    try: store.rename_speaker(asset_id,speaker_id,body.display_name.strip()); return {"ok":True}
    except KeyError: raise HTTPException(404,"Speaker not found")

app.mount("/",StaticFiles(directory="static",html=True),name="static")
