"""Exercise recorded Sarvam-shaped output without spending API credits."""
import json
import tempfile
from pathlib import Path

from speechkit.normalize import normalize_batch_output
from speechkit.storage import Storage

fixture = Path(__file__).parents[1] / "tests" / "fixtures" / "sarvam_batch_output.json"
artifact = normalize_batch_output(asset_id="demo", filename="two-speaker.wav", duration_seconds=4.2, output=json.loads(fixture.read_text()), job_id="recorded-job", estimated_cost_inr=0.0525)
with tempfile.TemporaryDirectory() as directory:
    storage = Storage(Path(directory) / "speechlens.sqlite")
    storage.create_asset("demo", "two-speaker.wav")
    storage.save_artifact(artifact)
    print(storage.search("demo", "question")[0]["text"])
