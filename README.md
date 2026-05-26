# CoRaCMG

English | [中文](README.zh-CN.md)

CoRaCMG is a VS Code extension for automated commit message generation. It uses retrieval-augmented examples from a commit-message corpus and LLM-based generation to produce commit messages from Git diffs.

The RAG corpus and embedding resources used by this project are built from the ApacheCM dataset.

## Repository Layout

- `vscode_extension/`: VS Code extension UI and commands.
- `node_service/`: Node.js API service, orchestration layer, LLM provider integration, feedback queue, and model scoring logic.
- `backend/`: FastAPI retrieval/evaluation services, embedding models, FAISS retrieval, and SQLite-backed document lookup.
- `fusion_search/`: scripts for building full diff embeddings from ApacheCM data and exporting backend-ready RAG resources.
- `experiment/`: experiment configs, scripts, and evaluation workflows.
- `resource/`: local generated RAG resources. This directory is not committed.

## Data Source

The retrieval corpus is derived from the ApacheCM dataset. The expected raw input is a JSONL file whose records contain commit metadata and at least:

- `diff`
- `message`
- `repo`
- `commit_sha`

Place the ApacheCM full dataset at:

```text
fusion_search/data/raw/apachecm/full.jsonl
```


## Build RAG Resources

Create the FusionSearch environment:

```bash
cd fusion_search
conda env create -f environment.yml
conda activate diff_search
```

Build dense embedding indexes:

```bash
python main.py build-index codebert
python main.py build-index jina
```

Export the indexes into the backend `RESOURCE_PATH` format:

```bash
python main.py export-backend --output-dir ../resource
```

Verify that the exported resources can be loaded by the backend:

```bash
python verify_backend_resources.py --resource-dir ../resource --models codebert jina
```

The exported backend resource layout is:

```text
resource/
  docs.db
  docs.jsonl
  embeddings/
    codebert.doc_ids.npy
    codebert.vecs.npy
    jina.doc_ids.npy
    jina.vecs.npy
  faiss/
    codebert.index
    jina.index
```

The backend `commit_id` is the source row id (`0`, `1`, `2`, ...), and the same ids must be used by `docs.db` and `embeddings/*.doc_ids.npy`.

## Run Locally

### 1. Python backend

There are two supported backend modes.

#### Option A: single backend service

Use this for local development or simple end-to-end testing. Retrieval, embedding, and evaluation endpoints are served by one FastAPI process:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set RESOURCE_PATH=..\resource
set EMBEDDING_MODEL=codebert
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

When using this mode, point both Node backend URLs to the same service:

```bash
set RETRIEVAL_BACKEND_URL=http://127.0.0.1:8000
set EVALUATION_BACKEND_URL=http://127.0.0.1:8000
```

#### Option B: split retrieval and evaluation services

Use this for production-like deployment. Online retrieval/generation traffic and background evaluation traffic run in separate FastAPI processes:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set RESOURCE_PATH=..\resource
set EMBEDDING_MODEL=codebert
uvicorn app.main_retrieval:app --host 127.0.0.1 --port 8000
```

Run the evaluation service in a second terminal:

```bash
cd backend
.venv\Scripts\activate
set RESOURCE_PATH=..\resource
set EMBEDDING_MODEL=codebert
uvicorn app.main_evaluation:app --host 127.0.0.1 --port 8001
```

In this mode, configure Node with separate backend URLs:

```bash
set RETRIEVAL_BACKEND_URL=http://127.0.0.1:8000
set EVALUATION_BACKEND_URL=http://127.0.0.1:8001
```

Health checks:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8001/api/health
```

### 2. Node API service

```bash
cd node_service
npm install
set PORT=3001
set RETRIEVAL_BACKEND_URL=http://127.0.0.1:8000
set EVALUATION_BACKEND_URL=http://127.0.0.1:8001
npm run start
```

If you use feedback evaluation queues, also start Redis and run the worker:

```bash
npm run start:worker
```

### 3. VS Code extension

```bash
cd vscode_extension
npm install
npm run compile
```

Open `vscode_extension/` in VS Code and start the extension host with `F5`. For local development, set:

```text
auto-gen-message.apiUrl = http://127.0.0.1:3001/api
```

## Docker Deployment

The deployment compose file starts the retrieval backend, evaluation backend, Node API, Node worker, Redis, and MySQL:

```bash
docker compose -f docker-compose.deploy.yml up -d --build
```

Before starting Docker, make sure `resource/` has been generated from ApacheCM and contains `docs.db`, `faiss/`, and `embeddings/`.

See `DEPLOY.md` for the fuller deployment workflow and operational notes.

## Useful Checks

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8001/api/health
curl http://127.0.0.1:3001/api/health
```
