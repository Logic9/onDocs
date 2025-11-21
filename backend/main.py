import os
import uuid
import time
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
import torch

# 캐시 설정
set_llm_cache(InMemoryCache())

UPLOAD_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MODEL_NAME = "gemma3n:e2b" 

# 임베딩 설정
torch.set_num_threads(4) 
EMBEDDING_MODEL = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask",
    model_kwargs={'device': 'cpu'}, 
    encode_kwargs={'normalize_embeddings': True, 'batch_size': 1}
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
        
        CHUNK_SIZE = 1000
        CHUNK_OVERLAP = 200

        if file_ext == ".pdf": 
            md_text = pymupdf4llm.to_markdown(file_path)
            raw_docs = [Document(page_content=md_text, metadata={"source": file_path})]
            text_splitter = MarkdownTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        elif file_ext in [".txt", ".md"]: 
            loader = TextLoader(file_path, encoding="utf-8")
            raw_docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        else:
            processing_status[filename] = "failed"
            return

        splits = text_splitter.split_documents(raw_docs)
        if len(splits) > 0:
            LATEST_DOC_HEADER = splits[0].page_content
                   
        vector_store = FAISS.from_documents(documents=splits, embedding=EMBEDDING_MODEL)
        bm25_retriever = BM25Retriever.from_documents(splits, preprocess_func=korean_tokenizer)
        bm25_retriever.k = 4
        
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
            import shutil
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
        chunk_sum = 1500
        if ext == ".pdf": 
            md_text = pymupdf4llm.to_markdown(file_path)
            raw_docs = [Document(page_content=md_text, metadata={"source": file_path})]
            text_splitter = MarkdownTextSplitter(chunk_size=chunk_sum, chunk_overlap=200)
        else: 
            loader = TextLoader(file_path, encoding="utf-8")
            raw_docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_sum, chunk_overlap=200)
            
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

        summary_llm = ChatOllama(model=MODEL_NAME, temperature=0, num_ctx=3072)
        summary_template = """[지시] 문서를 한국어로 3문단 이내로 요약해.\n[텍스트]\n"{text}"\n[요약]"""
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
        t0 = time.time()
        
        if not vector_store:
            yield "문서 분석이 완료되지 않았습니다."
            return
    
        try:
            # 검색 (Retrieval)
            faiss_retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
            bm25_retriever.k = 4
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, faiss_retriever],
                weights=[0.5, 0.5]
            )
            retrieved_docs = await ensemble_retriever.ainvoke(request.question)
            
            top_docs = retrieved_docs[:4]
            
            print("\n🔍 [DEBUG] Retrieved Chunks:")
            for i, doc in enumerate(top_docs):
                print(f"--- Chunk {i+1} ---\n{doc.page_content[:100]}...\n")

            combined_docs_content = []
            header_included = False
            for doc in top_docs:
                if doc.page_content == LATEST_DOC_HEADER:
                    header_included = True
                combined_docs_content.append(doc.page_content)
            if not header_included and LATEST_DOC_HEADER:
                combined_docs_content.insert(0, LATEST_DOC_HEADER)

            context_text = "\n\n====================\n".join(combined_docs_content)
            
            final_prompt = f"""
            [지시]
            너는 아래 [참고 자료]에 있는 내용만을 사용하여 질문에 한국어로 답해라.
            만약 [참고 자료]에 정답이 없다면, 절대 지어내지 말고 "문서에 해당 내용이 없습니다."라고 답해라.
            
            [참고 자료]
            {context_text}
            
            [질문]
            {request.question}
            
            [답변]
            """
            
            llm = ChatOllama(
                model=MODEL_NAME, 
                temperature=0, 
                num_ctx=2048, 
                num_thread=4,
                keep_alive="60m"
            )
            
            full_messages = [("human", final_prompt)]
            
            print(f"⏱️ [Perf] Sending to LLM... (Length: {len(final_prompt)} chars)")
            
            first_token_received = False
            async for chunk in llm.astream(full_messages):
                if not first_token_received:
                    t2 = time.time()
                    print(f"⚡ [Perf] Time to First Token: {t2 - t0:.3f}s")
                    first_token_received = True
                
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            print(f"Chat Error: {e}")
            yield f"❌ 오류 발생: {str(e)}"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)