# onDocs

> 100% Offline, Edge AI Document Analyzer

**onDocs**는 인터넷 연결 없이 로컬 환경에서 보안 걱정 없이 문서를 분석하는 경량 AI 서비스입니다.

## 🏆 Project for Open Source SW Competition

- **Team:** 피나클
- **Development Period:** 2025.11.20 ~ 2025.11.23

## 🛠 Tech Stack

### Core AI

- **Ollama** (`gemma3n:e2b`)

### Backend

- **Web Framework:** FastAPI, Uvicorn
- **LangChain Ecosystem:**
  - langchain, langchain-core, langchain-community
  - langchain-ollama, langchain-huggingface
  - langchain-text-splitters
- **AI & Embeddings:**
  - torch, transformers, huggingface-hub
  - HuggingFace Embeddings (`jhgan/ko-sroberta-multitask`)
- **Vector Store:** FAISS (faiss-cpu)
- **Retrieval:** BM25Retriever
- **Clustering:** scikit-learn (KMeans)
- **Text Processing:** numpy, kiwipiepy (Kiwi 형태소 분석기)
- **PDF → Markdown:** PyMuPDF4LLM
- **ONNX:** onnx, onnxruntime, onnxscript

### Frontend

- **Framework:** Next.js (v16), React (v19)
- **Styling:** Tailwind CSS, @tailwindcss/typography
- **Markdown Rendering:** react-markdown, remark-gfm
- **Icons:** lucide-react
- **HTTP Client:** axios

### Dev Tools

- **Lint:** ESLint, eslint-config-next
- **Tailwind/PostCSS:** @tailwindcss/postcss, tailwindcss

---

> **onDocs**는 오픈소스 SW 경진대회를 위해 개발된, 완전 오프라인 기반의 문서 분석 AI 서비스입니다.
