import os
import shutil
import uuid
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- LangChain Imports ---
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- 설정 ---
UPLOAD_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MODEL_NAME = "gemma3n:e2b"

# [성능 최적화] 한국어 임베딩 모델 (CPU 고속)
EMBEDDING_MODEL = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

app = FastAPI(title="onDocs API", description="High Performance Offline RAG")

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 전역 변수 ---
vector_store = None
processing_status: Dict[str, str] = {}

# --- 데이터 모델 ---
class ChatRequest(BaseModel):
    question: str

# --- 백그라운드 작업 함수 ---
def process_document(file_path: str, file_ext: str, filename: str):
    global vector_store, processing_status
    
    try:
        processing_status[filename] = "processing"
        
        # 1. 로더 선택
        if file_ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_ext in [".txt", ".md"]:
            loader = TextLoader(file_path, encoding="utf-8")
        else:
            processing_status[filename] = "failed"
            return

        docs = loader.load()
        
        # 청크 사이즈 800
        # 문맥이 잘리지 않도록 덩어리를 키움
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        splits = text_splitter.split_documents(docs)

        # 2. 고속 임베딩 생성
        vector_store = FAISS.from_documents(documents=splits, embedding=EMBEDDING_MODEL)
        
        processing_status[filename] = "completed"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        processing_status[filename] = "failed"

# --- API 엔드포인트 ---

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

@app.post("/chat")
async def chat(request: ChatRequest):
    global vector_store
    
    async def generate():
        if not vector_store:
            yield "문서 분석이 완료되지 않았습니다."
            return
    
        try:
            # MMR 검색 적용 & 개수 증가 (k=7)
            # MMR: 단순히 비슷한 것만 찾지 않고, 내용이 다양한 7개를 가져옴
            retriever = vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 7,           # 가져올 최종 문서 개수 (3 -> 7로 증가)
                    "fetch_k": 30,    # 후보로 검토할 문서 개수 (넓게 훑어봄)
                    "lambda_mult": 0.7 # 다양성 비율 (0.5~0.8 추천)
                }
            )
            docs = await retriever.ainvoke(request.question)
            context_text = "\n\n".join([doc.page_content for doc in docs])
            
            system_prompt = f"""
            당신은 문서를 기반으로 사용자의 모든 요청을 유연하게 처리하는 'onDocs AI'입니다.
            아래 [Context]를 철저히 분석하여 질문에 답변하세요.

            [핵심 행동 지침]
            1. **의도 파악 및 대응**: 질문의 의도를 스스로 파악하여 가장 적절한 형식으로 답변하세요.
               - **사실 질문**: 문서에 있는 팩트(숫자, 명칭)를 정확하게 인용하세요.
               - **요약/정리**: "요약해줘" 등의 요청엔 핵심 내용을 불릿 포인트(`-`)나 번호 매기기로 구조화하세요.
               - **비교/분석**: "표로 만들어줘" 등의 요청엔 Markdown Table 형식을 사용하세요.
               - **번역**: 다른 언어로 질문하거나 요청하면 해당 언어로 답변하세요.

            2. **신뢰성 유지**:
               - 답변의 근거는 반드시 [Context] 안에 있어야 합니다.
               - 문맥상 정답이 없다면 솔직하게 "문서에 해당 내용이 명시되어 있지 않습니다"라고 답하세요. 절대 지어내지 마세요.

            3. **답변 스타일**:
               - 서론("문서를 분석해보니...")과 결론("도움이 되셨나요?") 같은 군더더기를 빼고, **본론만 간결하게** 말하세요.
            
            [Context]:
            {context_text}
            """
            
            llm = ChatOllama(model=MODEL_NAME, temperature=0)
            messages = [("system", system_prompt), ("human", request.question)]
            
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)