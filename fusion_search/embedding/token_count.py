import argparse
import json
import random

import tiktoken
from tqdm import tqdm

SAMPLE_SIZE = 2000
SEED = 42


def count_tokens(text: str, enc) -> int:
    return len(enc.encode(text))


def estimate_tokens(jsonl_path, sample_size=SAMPLE_SIZE, seed=SEED, encoding="cl100k_base"):
    enc = tiktoken.get_encoding(encoding)
    diffs = []

    print("[INFO] Loading diffs...")
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            diff = item.get("diff", "")
            if diff:
                diffs.append(diff)

    total = len(diffs)
    print(f"[INFO] Total diffs: {total}")

    if not diffs:
        print("[INFO] No diffs found.")
        return

    random.seed(seed)
    sample = diffs if total <= sample_size else random.sample(diffs, sample_size)

    print(f"[INFO] Sampling {len(sample)} diffs for token estimation...")

    token_counts = []
    for d in tqdm(sample):
        token_counts.append(count_tokens(d, enc))

    token_counts.sort()

    avg = sum(token_counts) / len(token_counts)
    p95 = token_counts[int(len(token_counts) * 0.95)]
    max_v = token_counts[-1]

    estimated_total = avg * total

    print("\n===== Token Estimation Result =====")
    print(f"Average tokens / diff : {avg:.2f}")
    print(f"P95 tokens / diff     : {p95}")
    print(f"Max tokens / diff     : {max_v}")
    print(f"Estimated TOTAL tokens: {int(estimated_total):,}")
    print("==================================")


def main():
    parser = argparse.ArgumentParser(description="Estimate token counts for diff JSONL data.")
    parser.add_argument("input", help="Input JSONL path.")
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--encoding", default="cl100k_base")
    args = parser.parse_args()
    estimate_tokens(args.input, args.sample_size, args.seed, args.encoding)


if __name__ == "__main__":
    main()
