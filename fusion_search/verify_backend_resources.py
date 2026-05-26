# -*- coding: utf-8 -*-
import argparse
import os
import sys
from pathlib import Path

import numpy as np

from project_paths import resolve_project_path


def verify_backend_resources(resource_dir, models):
    resource_dir = resolve_project_path(resource_dir)
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    os.environ["RESOURCE_PATH"] = str(resource_dir)
    os.environ["EMBEDDING_MODEL"] = "all" if len(models) > 1 else models[0]

    from app.core.resources import resource_manager
    from app.retrieval.faiss_retriever import FaissRetriever

    resource_manager.initialized = False
    resource_manager.initialize(str(resource_dir))

    if resource_manager.db_conn is None:
        raise RuntimeError(f"docs.db was not loaded from {resource_dir}")

    cursor = resource_manager.db_conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM docs")
        doc_count = int(cursor.fetchone()[0])
    finally:
        cursor.close()

    print(f"[INFO] docs.db rows={doc_count}")

    retriever = FaissRetriever()
    for model_name in models:
        if model_name not in resource_manager.faiss_indices:
            raise RuntimeError(f"{model_name} FAISS index was not loaded")
        if model_name not in resource_manager.doc_id_maps:
            raise RuntimeError(f"{model_name} doc id map was not loaded")

        index = resource_manager.faiss_indices[model_name]
        doc_ids = resource_manager.doc_id_maps[model_name]
        vecs_path = resource_dir / "embeddings" / f"{model_name}.vecs.npy"
        if not vecs_path.exists():
            raise FileNotFoundError(vecs_path)

        vecs = np.load(vecs_path, mmap_mode="r")
        first_vector = np.asarray(vecs[0], dtype=np.float32)
        results = retriever.search_by_vector(first_vector.tolist(), model_name=model_name, top_k=1)
        if not results:
            raise RuntimeError(f"{model_name} returned no retrieval result")

        print(
            f"[INFO] {model_name}: index_ntotal={index.ntotal} "
            f"doc_ids={len(doc_ids)} top_commit_id={results[0]['commit_id']}"
        )

    print("[DONE] Backend resources are loadable.")


def main():
    parser = argparse.ArgumentParser(description="Smoke test backend RESOURCE_PATH files.")
    parser.add_argument("--resource-dir", default="artifacts/backend_resource")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["codebert", "jina"],
        choices=["codebert", "jina"],
    )
    args = parser.parse_args()
    verify_backend_resources(args.resource_dir, args.models)


if __name__ == "__main__":
    main()
