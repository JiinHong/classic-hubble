"""Build-time download of fixed official model archives, with SHA-256 checks."""

import hashlib
import io
import shutil
import sys
import tarfile
from pathlib import Path
from urllib.request import urlopen

MODELS = {
    "PP-OCRv5_mobile_det": "50446e5d01ac2a73d5319c89513281f6578414c888c602f9af13f93feefffc58",
    "korean_PP-OCRv5_mobile_rec": "a6261f800ad335aa6ef77b6f7c4dcedfd5e11b95f4d70982d41ee31c2ace5e66",
}
BASE = "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0"


def main(root: Path):
    for name, expected in MODELS.items():
        with urlopen(f"{BASE}/{name}_infer.tar", timeout=120) as response:
            content = response.read(100 * 1024 * 1024 + 1)
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Model archive checksum changed: {name}")
        destination = root / name
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(content)) as archive:
            for filename in ("inference.yml", "inference.json", "inference.pdiparams"):
                member = archive.getmember(f"{name}_infer/{filename}")
                if not member.isfile():
                    raise ValueError("Model member must be a regular file")
                with (
                    archive.extractfile(member) as source,
                    (destination / filename).open("wb") as target,
                ):
                    shutil.copyfileobj(source, target)
        print(f"Bundled {name}: {expected}", flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
