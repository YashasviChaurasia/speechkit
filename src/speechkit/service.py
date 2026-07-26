from __future__ import annotations
import shutil, uuid
from pathlib import Path
from .media import extract_audio, inspect_media
from .normalize import normalize_batch_output
from .sarvam_provider import SarvamProvider
from .storage import Storage

class SpeechService:
    def __init__(self, storage: Storage, provider: SarvamProvider, data_dir: Path, ffmpeg: str="ffmpeg", ffprobe: str="ffprobe"):
        self.storage,self.provider,self.data_dir,self.ffmpeg,self.ffprobe=storage,provider,data_dir,ffmpeg,ffprobe
    def process(self, filename: str, upload: Path, num_speakers: int|None=None) -> str:
        asset_id=uuid.uuid4().hex; work=self.data_dir/asset_id; work.mkdir(parents=True); original=work/filename; shutil.move(str(upload), original)
        self.storage.create_asset(asset_id, filename)
        try:
            self.storage.set_status(asset_id,"extracting_audio"); info=inspect_media(original,self.ffprobe)
            wav=extract_audio(original,work/"audio.wav",self.ffmpeg)
            self.storage.set_status(asset_id,"submitting"); output,job_id,failed=self.provider.transcribe_batch(wav,num_speakers=num_speakers)
            self.storage.set_status(asset_id,"normalising"); estimate=round(info.duration_seconds/3600*(45 if num_speakers is not None else 45),4)
            artifact=normalize_batch_output(asset_id=asset_id,filename=filename,duration_seconds=info.duration_seconds,output=output,job_id=job_id,estimated_cost_inr=estimate,file_failures=failed)
            artifact.metadata["language_code"]=artifact.language_code; artifact.metadata["media_path"]=str(original); self.storage.save_artifact(artifact); return asset_id
        except Exception as e: self.storage.set_status(asset_id,"failed",str(e)); raise
