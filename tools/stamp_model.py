"""Stamp extraction_metadata.model on staged extractions.

The model id is the run setting of the extraction session, recorded by the orchestration session
after a batch lands. The extracting agent does not report it: an agent cannot reliably state its
own model id, and the 2026-08-17 corpus carries 13 different spellings of it in `extractor`.

Refuses to overwrite a different value already present — a mismatch means the file came from
another run, and that is a question, not something to fix silently. Re-running with the same id
is a no-op.

Usage:  python3 stamp_model.py <model_id> <STUDY> [<STUDY> ...]
        e.g. python3 stamp_model.py claude-opus-5-5 NCT02107703 NCT01847274
"""

import json
import os
import re
import sys
from pathlib import Path

STAGING = Path(os.environ.get("SOA2USDM_STAGING", "staging"))
MODEL_ID = re.compile(r"^claude-[a-z0-9-]+$")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    model, studies = sys.argv[1], sys.argv[2:]
    if not MODEL_ID.match(model):
        sys.exit(f"not an API model id: {model!r} (expected e.g. 'claude-opus-5-5')")

    n_stamped = n_same = 0
    for study in studies:
        files = sorted((STAGING / study).glob(f"{study}_Table_*_extraction.json"))
        if not files:
            sys.exit(f"no extraction JSON in {STAGING / study}")
        for path in files:
            data = json.loads(path.read_text())
            em = data["extraction_metadata"]
            have = em.get("model")
            if have == model:
                n_same += 1
                continue
            if have is not None:
                sys.exit(f"{path.name}: model already {have!r}, not overwriting with {model!r}")
            em["model"] = model
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            n_stamped += 1
            print(f"stamped {path.name}")

    print(f"{n_stamped} stamped, {n_same} already {model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
