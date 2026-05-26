# CoRaCMG

[English](README.md) | 中文

CoRaCMG 是一个用于自动生成 commit message 的 VS Code 扩展。它会从提交信息语料库中检索相似示例，并结合大语言模型，根据 Git diff 生成提交信息。

本项目使用的 RAG 语料和 embedding 资源来自 ApacheCM 数据集。

## 仓库结构

- `vscode_extension/`：VS Code 扩展 UI 和命令。
- `node_service/`：Node.js API 服务、生成编排、LLM provider 集成、反馈队列和模型评分逻辑。
- `backend/`：FastAPI 检索/评估服务、embedding 模型、FAISS 检索和 SQLite 文本库查询。
- `fusion_search/`：基于 ApacheCM 构建全量 diff embedding，并导出后端可加载 RAG 资源的脚本。
- `experiment/`：实验配置、脚本和评估流程。
- `resource/`：本地生成的 RAG 资源目录，不提交到 Git。

## 数据来源

检索语料来自 ApacheCM 数据集。原始输入应为 JSONL 文件，每条记录包含提交元数据，并至少包含：

- `diff`
- `message`
- `repo`
- `commit_sha`

将 ApacheCM 全量数据放到：

```text
fusion_search/data/raw/apachecm/full.jsonl
```


## 构建 RAG 资源

创建 FusionSearch 环境：

```bash
cd fusion_search
conda env create -f environment.yml
conda activate diff_search
```

构建 dense embedding 索引：

```bash
python main.py build-index codebert
python main.py build-index jina
```

把索引导出为后端 `RESOURCE_PATH` 格式：

```bash
python main.py export-backend --output-dir ../resource
```

验证导出的资源能被后端加载：

```bash
python verify_backend_resources.py --resource-dir ../resource --models codebert jina
```

导出的后端资源结构如下：

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

后端返回的 `commit_id` 是源数据顺序 id（`0`、`1`、`2`、...），`docs.db` 和 `embeddings/*.doc_ids.npy` 必须使用同一套 id。

## 本地运行

### 1. Python 后端

后端支持两种运行方式。

#### 方式 A：单服务运行

适合本地开发或简单端到端测试。检索、embedding 和评估接口都由同一个 FastAPI 进程提供：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set RESOURCE_PATH=..\resource
set EMBEDDING_MODEL=codebert
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

使用这种方式时，Node 侧两个后端 URL 都指向同一个服务：

```bash
set RETRIEVAL_BACKEND_URL=http://127.0.0.1:8000
set EVALUATION_BACKEND_URL=http://127.0.0.1:8000
```

#### 方式 B：拆分检索和评估服务

适合更接近生产部署的场景。在线检索/生成流量和后台评估流量由两个 FastAPI 进程分别处理：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set RESOURCE_PATH=..\resource
set EMBEDDING_MODEL=codebert
uvicorn app.main_retrieval:app --host 127.0.0.1 --port 8000
```

在第二个终端运行评估服务：

```bash
cd backend
.venv\Scripts\activate
set RESOURCE_PATH=..\resource
set EMBEDDING_MODEL=codebert
uvicorn app.main_evaluation:app --host 127.0.0.1 --port 8001
```

使用这种方式时，Node 侧配置两个不同的后端 URL：

```bash
set RETRIEVAL_BACKEND_URL=http://127.0.0.1:8000
set EVALUATION_BACKEND_URL=http://127.0.0.1:8001
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8001/api/health
```

### 2. Node API 服务

```bash
cd node_service
npm install
set PORT=3001
set RETRIEVAL_BACKEND_URL=http://127.0.0.1:8000
set EVALUATION_BACKEND_URL=http://127.0.0.1:8001
npm run start
```

如果使用反馈评估队列，还需要启动 Redis 并运行 worker：

```bash
npm run start:worker
```

### 3. VS Code 扩展

```bash
cd vscode_extension
npm install
npm run compile
```

在 VS Code 中打开 `vscode_extension/`，按 `F5` 启动扩展宿主。 本地开发时将扩展配置设为：

```text
auto-gen-message.apiUrl = http://127.0.0.1:3001/api
```

## Docker 部署

部署 compose 文件会启动检索后端、评估后端、Node API、Node worker、Redis 和 MySQL：

```bash
docker compose -f docker-compose.deploy.yml up -d --build
```

启动 Docker 前，请确认 `resource/` 已经基于 ApacheCM 生成，并包含 `docs.db`、`faiss/` 和 `embeddings/`。

更完整的部署流程和运维说明见 `DEPLOY.md`。

## 常用检查

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8001/api/health
curl http://127.0.0.1:3001/api/health
```
