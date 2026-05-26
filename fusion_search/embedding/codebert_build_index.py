# -*- coding: utf-8 -*-
"""
CodeBERT diff embedding index builder (with L2 normalization)
- Only uses `diff` field from jsonl
- Model: microsoft/codebert-base
- Output: pickle index for semantic retrieval
"""

import json
import sys
import pickle
import argparse
from pathlib import Path
import torch
import numpy as np
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_paths import INDEX_DIR, RAW_DATA_DIR, resolve_project_path


# -----------------------------
# Configuration
# -----------------------------
MODEL_NAME = "microsoft/codebert-base"
MAX_LENGTH = 512
BATCH_SIZE = 8
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_INDEX = INDEX_DIR / "codebert_diff_index.pkl"


# -----------------------------
# Load JSONL
# -----------------------------
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


# -----------------------------
# CodeBERT Encoder
# -----------------------------
class CodeBERTEncoder:
    def __init__(self, model_name, device):
        # 使用 AutoTokenizer + AutoModel 可以自动匹配 Roberta/Bert checkpoint
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(device)
        self.model.eval()
        self.device = device

    @torch.no_grad()
    def encode(self, texts):
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt"
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        outputs = self.model(**inputs)

        last_hidden = outputs.last_hidden_state  # (B, L, H)
        attention_mask = inputs["attention_mask"].unsqueeze(-1)

        masked_hidden = last_hidden * attention_mask
        sum_hidden = masked_hidden.sum(dim=1)
        lengths = attention_mask.sum(dim=1)

        embeddings = sum_hidden / lengths  # (B, H)
        # L2 normalization
        norms = np.linalg.norm(embeddings.cpu().numpy(), axis=1, keepdims=True)
        embeddings = embeddings.cpu().numpy() / norms

        return embeddings


# -----------------------------
# Main
# -----------------------------
def build_codebert_index(
    jsonl_path,
    output_index=OUTPUT_INDEX,
    model_name=MODEL_NAME,
    batch_size=BATCH_SIZE,
    device=DEVICE,
):
    jsonl_path = resolve_project_path(jsonl_path)
    output_index = resolve_project_path(output_index)
    output_index.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Device: {device}")
    if device == "cuda":
        print(f"[INFO] CUDA is available. Using GPU: {torch.cuda.get_device_name(torch.cuda.current_device())}")
    else:
        print("[INFO] CUDA is not available. Using CPU.")

    print("[INFO] Loading diffs...")
    diffs, raw_items = load_diffs(jsonl_path)
    print(f"[INFO] Loaded {len(diffs)} entries")

    print("[INFO] Loading CodeBERT model...")
    encoder = CodeBERTEncoder(model_name, device)

    print("[INFO] Encoding diffs...")
    all_embeddings = []
    for i in tqdm(range(0, len(diffs), batch_size)):
        batch = diffs[i:i + batch_size]
        emb = encoder.encode(batch)
        all_embeddings.append(emb)

    embeddings = np.vstack(all_embeddings)  # (N, H)

    print("[INFO] Saving embedding index...")
    with open(output_index, "wb") as f:
        pickle.dump(
            {
                "embeddings": embeddings,
                "raw_items": raw_items,
                "model": model_name
            },
            f
        )

    print(f"[INFO] Index saved to {output_index}")
    print(f"[INFO] Embedding shape: {embeddings.shape}")


def main():
    parser = argparse.ArgumentParser(description="Build a CodeBERT embedding index for diff JSONL data.")
    parser.add_argument("input", nargs="?", default=RAW_DATA_DIR / "apachecm" / "full.jsonl")
    parser.add_argument("--output", default=OUTPUT_INDEX)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--device", default=DEVICE)
    args = parser.parse_args()
    build_codebert_index(args.input, args.output, args.model, args.batch_size, args.device)


if __name__ == "__main__":
    main()
