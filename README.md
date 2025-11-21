# onDocs

> 100% Offline, Edge AI Document Analyzer

**onDocs**는 인터넷 연결 없이 로컬 환경에서 보안 걱정 없이 문서를 분석하는 경량 AI 서비스입니다.

## 🏆 Project for Open Source SW Competition

- **Team:** 피나클
- **Development Period:** 2025.11.20 ~ 2025.11.23

## 🛠 Tech Stack

- **Core AI:** Ollama (`gemma3n:e2b`)
- **Backend:**
  - FastAPI
  - LangChain (langchain, langchain_ollama, langchain_huggingface, langchain_community, langchain_core, langchain_text_splitters)
  - FAISS
  - HuggingFace Embeddings (`jhgan/ko-sroberta-multitask`)
  - BM25Retriever
  - Kiwi 형태소 분석기 (`kiwipiepy`)
  - PyMuPDF4LLM (PDF → Markdown 변환)
  - scikit-learn (KMeans 클러스터링)
  - numpy
- **Frontend:** Next.js, Tailwind CSS
