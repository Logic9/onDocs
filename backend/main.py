import os
import shutil
import uuid
import re
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- LangChain & AI Imports ---
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document 
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.cache import InMemoryCache
from langchain.globals import set_llm_cache
from langchain_core.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from kiwipiepy import Kiwi
from sklearn.cluster import KMeans
import numpy as np
import pymupdf4llm 

set_llm_cache(InMemoryCache())

# --- 설정 ---
UPLOAD_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MODEL_NAME = "gemma3n:e2b" 

EMBEDDING_MODEL = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask",
    model_kwargs={'device': 'cpu'}, 
    encode_kwargs={'normalize_embeddings': True, 'batch_size': 16} 
)

kiwi = Kiwi()
def korean_tokenizer(text: str) -> List[str]:
    return [token.form for token in kiwi.tokenize(text)]

app = FastAPI(title="onDocs API", description="General Purpose Precision RAG")

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store = None
bm25_retriever = None
processing_status: Dict[str, str] = {}
LATEST_DOC_HEADER = "" 

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    history: List[Message] = []

class SummarizeRequest(BaseModel):
    filename: str

def process_document(file_path: str, file_ext: str, filename: str):
    global vector_store, bm25_retriever, processing_status, LATEST_DOC_HEADER
    
    try:
        processing_status[filename] = "processing"
        
        raw_docs = []
        
        if file_ext == ".pdf": 
            md_text = pymupdf4llm.to_markdown(file_path)
            raw_docs = [Document(page_content=md_text, metadata={"source": file_path})]
            text_splitter = MarkdownTextSplitter(chunk_size=1200, chunk_overlap=300)
            
        elif file_ext in [".txt", ".md"]: 
            loader = TextLoader(file_path, encoding="utf-8")
            raw_docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300)
        else:
            processing_status[filename] = "failed"
            return

        splits = text_splitter.split_documents(raw_docs)

        if len(splits) > 0:
            LATEST_DOC_HEADER = splits[0].page_content
                   
        vector_store = FAISS.from_documents(documents=splits, embedding=EMBEDDING_MODEL)
        bm25_retriever = BM25Retriever.from_documents(splits, preprocess_func=korean_tokenizer)
        bm25_retriever.k = 5 
        
        processing_status[filename] = "completed"
        
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        processing_status[filename] = "failed"

@app.get("/")
def health_check():
    return {"status": "online", "model": MODEL_NAME}

@app.get("/status/{filename}")
def get_status(filename: str):
    status = processing_status.get(filename, "unknown")
    return {"status": status}

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    global processing_status
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")

    if file_ext not in [".pdf", ".txt", ".md"]:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")

    processing_status[file.filename] = "pending"
    background_tasks.add_task(process_document, file_path, file_ext, file.filename)
    
    return {"message": "Upload started", "filename": file.filename}

@app.post("/summarize")
async def summarize_document(request: SummarizeRequest):
    filename = request.filename
    file_path = None
    for f in os.listdir(UPLOAD_DIR):
        if f.endswith(filename):
            file_path = os.path.join(UPLOAD_DIR, f)
            break   
    if not file_path: raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    try:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf": 
            md_text = pymupdf4llm.to_markdown(file_path)
            raw_docs = [Document(page_content=md_text, metadata={"source": file_path})]
            text_splitter = MarkdownTextSplitter(chunk_size=2000, chunk_overlap=200)
        else: 
            loader = TextLoader(file_path, encoding="utf-8")
            raw_docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
            
        docs = text_splitter.split_documents(raw_docs)
        
        if len(docs) > 10:
            vectors = EMBEDDING_MODEL.embed_documents([d.page_content for d in docs])
            vectors = np.array(vectors)
            num_clusters = 5
            kmeans = KMeans(n_clusters=num_clusters, random_state=42).fit(vectors)
            closest_indices = []
            for i in range(num_clusters):
                distances = np.linalg.norm(vectors - kmeans.cluster_centers_[i], axis=1)
                closest_index = np.argmin(distances)
                closest_indices.append(closest_index)
            selected_docs = [docs[i] for i in sorted(closest_indices)]
        else:
            selected_docs = docs

        summary_llm = ChatOllama(model=MODEL_NAME, temperature=0, num_ctx=4096)
        
        summary_template = """
        [지시]
        문서를 한국어로 3문단 이내로 요약해 줘.
        표(Table)나 주요 일정(날짜)이 있다면 그 내용을 반드시 포함해서 정리해.
        
        [텍스트]
        "{text}"
        
        [요약]
        """
        SUMMARY_PROMPT = PromptTemplate.from_template(summary_template)
        chain = load_summarize_chain(summary_llm, chain_type="stuff", prompt=SUMMARY_PROMPT)
        
        summary_result = await chain.ainvoke(selected_docs)
        return {"summary": summary_result["output_text"]}
    except Exception as e:
        print(f"Summarize Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    global vector_store, bm25_retriever, LATEST_DOC_HEADER
    
    async def generate():
        if not vector_store:
            yield "문서 분석이 완료되지 않았습니다."
            return
    
        try:
            faiss_retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
            bm25_retriever.k = 5
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, faiss_retriever],
                weights=[0.2, 0.8] 
            )
            retrieved_docs = await ensemble_retriever.ainvoke(request.question)
            
            top_docs = retrieved_docs[:2] 

            # Header Injection
            combined_docs_content = []
            header_included = False
            for doc in top_docs:
                if doc.page_content == LATEST_DOC_HEADER:
                    header_included = True
                combined_docs_content.append(doc.page_content)
            
            if not header_included and LATEST_DOC_HEADER:
                combined_docs_content.insert(0, LATEST_DOC_HEADER)
                print("📌 [System] Header 강제 주입됨")

            context_text = "\n---\n".join(combined_docs_content)
        
            system_prompt = f"""
            [지시]
            너는 문서를 정밀하게 분석하는 AI야. 아래 [문서 내용]을 보고 질문에 답해.
            
            [분석 핵심 규칙]
            1. **레이블(Label) 매칭:** 사용자가 특정 정보를 물어보면, 문서에서 그 단어(키워드)를 먼저 찾아.
               - 예: '공개 일자'를 물으면 -> 문서에서 '공개'라는 단어를 찾고 -> 그 **바로 옆이나 아래**에 있는 날짜를 답해.
               - 예: '출원 일자'를 물으면 -> 문서에서 '출원'이라는 단어를 찾고 -> 그 근처의 날짜를 답해.
            
            2. **유사한 정보 구분:**
               - 문서에 여러 개의 날짜나 이름이 섞여 있을 때, 질문한 키워드와 **물리적으로 가장 가까운** 값을 선택해야 해. 절대 추측하지 마.
            
            3. **동의어 처리:**
               - '제출'='신청'='접수' (같은 의미로 해석)
               - '마감'='종료'='까지'
            
            [문서 내용]
            {context_text}
            """
            
            llm = ChatOllama(
                model=MODEL_NAME, 
                temperature=0, 
                num_ctx=4096, 
                num_thread=4,
                keep_alive="60m"
            )

            full_messages = [("system", system_prompt)] 
            for msg in request.history[-2:]:
                role_map = {'assistant': 'ai', 'human': 'human', 'user': 'human', 'system': 'system'}
                full_messages.append((role_map.get(msg.role, 'human'), msg.content))
            
            full_messages.append(("human", request.question))
            
            async for chunk in llm.astream(full_messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            print(f"Chat Error: {e}")
            yield f"❌ 오류 발생: {str(e)}"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)