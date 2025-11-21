import os
import uuid
import re
import multiprocessing
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_ollama import ChatOllama
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document 
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.cache import InMemoryCache
from langchain.globals import set_llm_cache

from kiwipiepy import Kiwi
from transformers import AutoTokenizer
import onnxruntime as ort
import numpy as np
import pymupdf4llm 

# 캐시 설정
set_llm_cache(InMemoryCache())

UPLOAD_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MODEL_NAME = "gemma3n:e2b"

MAX_CONTEXT_WINDOW = 4096

# CPU 코어 수 자동 감지
NUM_CORES = multiprocessing.cpu_count()
NUM_THREADS = max(2, NUM_CORES) 
print(f"🚀 System Info: Using {NUM_THREADS} CPU threads for max performance.")

# 텍스트 다이어트
def clean_text(text: str) -> str:
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ONNX 임베딩
class OnnxQuantizedEmbeddings(Embeddings):
    def __init__(self, model_dir="./onnx_emb_model"):
        if not os.path.exists(model_dir):
            print(f"⚠️ 경고: {model_dir} 없음. 기본 모드로 동작합니다.")
            from langchain_huggingface import HuggingFaceEmbeddings
            self.fallback = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
            return

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = NUM_THREADS
        
        model_path = os.path.join(model_dir, "model_quantized.onnx")
        if not os.path.exists(model_path):
            model_path = os.path.join(model_dir, "model.onnx")
            
        providers = ['CPUExecutionProvider']
        
        self.session = ort.InferenceSession(model_path, sess_options, providers=providers)
        print(f"⚡ ONNX Loaded (Stable CPU Mode): {model_path}")
        self.fallback = None

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if self.fallback:
            return self.fallback.embed_documents(texts)

        inputs = self.tokenizer(
            texts, padding=True, truncation=True, max_length=512, return_tensors="np"
        )
        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64)
        }
        outputs = self.session.run(None, onnx_inputs)
        
        last_hidden_state = outputs[0]
        attention_mask = inputs["attention_mask"]
        
        input_mask_expanded = np.expand_dims(attention_mask, -1)
        input_mask_expanded = np.broadcast_to(input_mask_expanded, last_hidden_state.shape).astype(float)
        sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
        sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
        embeddings = sum_embeddings / sum_mask
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.clip(norm, a_min=1e-9, a_max=None)
        
        return embeddings.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]

# 임베딩 로드
try:
    EMBEDDING_MODEL = OnnxQuantizedEmbeddings()
except:
    from langchain_huggingface import HuggingFaceEmbeddings
    EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

kiwi = Kiwi()
def korean_tokenizer(text: str) -> List[str]:
    return [token.form for token in kiwi.tokenize(text)]

llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=MAX_CONTEXT_WINDOW,
    num_thread=NUM_THREADS,
    keep_alive="60m" 
)

app = FastAPI(title="onDocs API")

origins = ["*"]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

vector_store = None
bm25_retriever = None
processing_status: Dict[str, str] = {}
FULL_DOC_TEXT = "" 

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    history: List[Message] = []

class SummarizeRequest(BaseModel):
    filename: str

# ---------------------------------------------------------
# 문서 처리 (RAG + 인코딩 감지)
# ---------------------------------------------------------
def process_document(file_path: str, file_ext: str, filename: str):
    global vector_store, bm25_retriever, processing_status, FULL_DOC_TEXT
    
    try:
        processing_status[filename] = "processing"
        
        raw_text = ""
        if file_ext == ".pdf": 
            raw_text = pymupdf4llm.to_markdown(file_path)
        else:
            # 인코딩 자동 감지 (UTF-8 실패 시 CP949 시도)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
            except UnicodeDecodeError:
                print(f"⚠️ UTF-8 decoding failed for {filename}. Trying CP949 (EUC-KR)...")
                with open(file_path, 'r', encoding='cp949') as f:
                    raw_text = f.read()
        
        FULL_DOC_TEXT = clean_text(raw_text)
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        splits = text_splitter.create_documents([FULL_DOC_TEXT])

        # 벡터 스토어
        vector_store = FAISS.from_documents(documents=splits, embedding=EMBEDDING_MODEL)
        bm25_retriever = BM25Retriever.from_documents(splits, preprocess_func=korean_tokenizer)
        bm25_retriever.k = 4
        
        processing_status[filename] = "completed"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        processing_status[filename] = "failed"

@app.get("/status/{filename}")
def get_status(filename: str):
    return {"status": processing_status.get(filename, "unknown")}

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="파일 저장 실패")

    processing_status[file.filename] = "pending"
    background_tasks.add_task(process_document, file_path, file_ext, file.filename)
    return {"message": "Upload started"}

# ---------------------------------------------------------
# 요약 (RAG 모드 Context에 맞게 텍스트 길이 제한)
# ---------------------------------------------------------
@app.post("/summarize")
async def summarize_document(request: SummarizeRequest):
    if not FULL_DOC_TEXT:
        async def err(): yield "문서를 먼저 업로드해주세요."
        return StreamingResponse(err(), media_type="text/event-stream")

    async def generate_summary():
        limit = int(MAX_CONTEXT_WINDOW * 1.5 * 0.9)
        input_text = FULL_DOC_TEXT[:limit]
        
        prompt = f"""<start_of_turn>user
[지시]
아래 문서를 읽고 핵심 내용을 3문단 이내로 요약해.
중요한 수치나 결론은 반드시 포함해.

[문서]
{input_text}

[요약]<end_of_turn>
<start_of_turn>model
"""
        async for chunk in llm.astream(prompt):
            if chunk.content:
                yield chunk.content

    return StreamingResponse(generate_summary(), media_type="text/event-stream")

# ---------------------------------------------------------
# 채팅
# ---------------------------------------------------------
@app.post("/chat")
async def chat(request: ChatRequest):
    
    async def generate():
        if not vector_store:
            yield "문서 분석이 완료되지 않았습니다."
            return
    
        try:
            # Hybrid Search (RAG)
            faiss_retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, faiss_retriever],
                weights=[0.6, 0.4]
            )
            docs = await ensemble_retriever.ainvoke(request.question)
            
            # Context 구성
            context_str = "\n\n".join([d.page_content for d in docs])

            final_prompt = f"""<start_of_turn>user
당신은 문서를 분석하는 AI 비서입니다. 아래 [참고 자료]에 있는 사실만을 바탕으로 질문에 정확하게 한국어로 답변하세요.
없는 내용을 지어내지 말고, 자료에 명시된 내용을 찾아 답변하세요.

[참고 자료]
{context_str}

[질문]
{request.question}<end_of_turn>
<start_of_turn>model
"""
            
            async for chunk in llm.astream(final_prompt):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            print(f"Chat Error: {e}")
            yield f"오류: {str(e)}"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)