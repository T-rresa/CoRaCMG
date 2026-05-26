# -*- coding: utf-8 -*-
"""
Build diff embedding index using local jina-embeddings-v2-base-code
Only uses `diff` field from full.jsonl
"""

import json
import sys
import pickle
import argparse
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_paths import INDEX_DIR, RAW_DATA_DIR, resolve_project_path


#
# Config
#
MODEL_PATH = "jinaai/jina-embeddings-v2-base-code"
OUTPUT_PATH = INDEX_DIR / "jina_diff_index.pkl"
BATCH_SIZE = 2          # 本地模型建议稍小
MAX_SEQ_LENGTH = 4096     # 强烈建议裁剪，避免你之前看到的 token 爆炸

#
# Load JSONL
#
def load_diffs(jsonl_path):
    diffs = []
    raw_items = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON parse error at line {line_no}: {e}")

            diff = item.get("diff", "")
            diffs.append(diff)
            raw_items.append(item)

    return diffs, raw_items


#
# Main (Index Builder)
#
def build_jina_index(
    jsonl_path,
    output_path=OUTPUT_PATH,
    model_path=MODEL_PATH,
    batch_size=BATCH_SIZE,
    max_seq_length=MAX_SEQ_LENGTH,
):
    jsonl_path = resolve_project_path(jsonl_path)
    output_path = resolve_project_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("[INFO] Loading diffs...")
    diffs, raw_items = load_diffs(jsonl_path)
    print(f"[INFO] Loaded {len(diffs)} diffs")

    print(f"[INFO] Loading local embedding model from: {model_path}")

    model = SentenceTransformer(
        model_path,
        trust_remote_code=True,
    )
    model.max_seq_length = max_seq_length

    print("[INFO] Encoding diffs (local model)...")
    all_vectors = []

    for i in tqdm(range(0, len(diffs), batch_size)):
        batch = diffs[i : i + batch_size]

        vectors = model.encode(
            batch,
            batch_size=len(batch),
            show_progress_bar=False,
            normalize_embeddings=True,   # 内置 L2 normalize
        )

        all_vectors.append(vectors)

    embeddings = np.vstack(all_vectors)
    print(f"[INFO] Total embeddings shape: {embeddings.shape}")

    print(f"[INFO] Saving index to {output_path}...")
    with open(output_path, "wb") as f:
        pickle.dump(
            {
                "embeddings": embeddings,
                "raw_items": raw_items,
                "model_path": model_path,
                "max_seq_length": max_seq_length,
            },
            f,
        )

    print("[INFO] Index saved successfully.")


def main():
    parser = argparse.ArgumentParser(description="Build a Jina embedding index for diff JSONL data.")
    parser.add_argument("input", nargs="?", default=RAW_DATA_DIR / "apachecm" / "full.jsonl")
    parser.add_argument("--output", default=OUTPUT_PATH)
    parser.add_argument("--model", default=MODEL_PATH)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--max-seq-length", type=int, default=MAX_SEQ_LENGTH)
    args = parser.parse_args()
    build_jina_index(args.input, args.output, args.model, args.batch_size, args.max_seq_length)


if __name__ == "__main__":
    main()
