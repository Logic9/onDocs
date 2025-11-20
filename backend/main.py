import os
import shutil
import uuid
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- LangChain Imports ---
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- 설정 ---
UPLOAD_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MODEL_NAME = "gemma3n:e2b"

# MRL을 적용한 커스텀 임베딩 클래스
class MatryoshkaOllamaEmbeddings(OllamaEmbeddings):
    dimensions: int = 768 

    def __init__(self, model: str, dimensions: int = 768, **kwargs):
        super().__init__(model=model, **kwargs)
        self.dimensions = dimensions

    # 동기(Sync) 메서드 오버라이딩
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = super().embed_documents(texts)
        return [emb[:self.dimensions] for emb in embeddings]

    def embed_query(self, text: str) -> List[float]:
        embedding = super().embed_query(text)
        return embedding[:self.dimensions]
    
    # 비동기(Async) 메서드 오버라이딩
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = await super().aembed_documents(texts)
        return [emb[:self.dimensions] for emb in embeddings]

    async def aembed_query(self, text: str) -> List[float]:
        embedding = await super().aembed_query(text)
        return embedding[:self.dimensions]

# 임베딩 모델: EmbeddingGemma (Ollama QAT 버전)
EMBEDDING_MODEL = MatryoshkaOllamaEmbeddings(
    model="embeddinggemma:300m-qat-q8_0",
    dimensions=256 
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
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    history: List[Message] = []

# --- 백그라운드 작업 함수 ---
def process_document(file_path: str, file_ext: str, filename: str):
    global vector_store, processing_status
    
    try:
        processing_status[filename] = "processing"
        
        if file_ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_ext in [".txt", ".md"]:
            loader = TextLoader(file_path, encoding="utf-8")
        else:
            processing_status[filename] = "failed"
            return

        docs = loader.load()
        
        # 텍스트 분할 설정
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=100,
            separators=["\n", "\n\n", " ", ""] 
        )
        splits = text_splitter.split_documents(docs)

        # 임베딩 및 벡터 저장소 생성
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
            # MMR 검색 설정
            retriever = vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 6,           
                    "fetch_k": 20,     
                    "lambda_mult": 0.5
                }
            )
            docs = await retriever.ainvoke(request.question)
            context_text = "\n\n".join([doc.page_content for doc in docs])
            
            # 시스템 프롬프트
            system_prompt = f"""
            당신은 제공된 [Context]를 바탕으로 사용자 질문에 대해 가장 관련성 높은 사실만을 추출하여 답변하는 AI 문서 분석기 'onDocs AI'입니다.

            [지침]
            1. 답변의 모든 내용은 오직 [Context] 내의 정보만을 사용해야 합니다.
            2. 답변 생성 원칙:
               - [Context]에 질문에 대한 정보가 **포함되어 있다면**, 다른 서론 없이 바로 답변의 본론을 시작하세요.
               - [Context]가 **질문과 완전히 무관하거나 비어 있다면**에만 한하여, "문서에 해당 내용이 명시되어 있지 않습니다"라고 간결하게 답하세요.
               - **절대 '죄송합니다', '제가 앞서 제공한 정보에는' 같은 불필요한 사과나 모순된 문장을 사용하지 마세요.**
            3. 답변은 서론이나 군더더기 없이 바로 본론부터 시작하고, Markdown 형식을 활용하여 질문 의도에 가장 적절한 형식(목록, 표 등)으로 구성하세요.
            4. 사용자가 다른 언어로 질문하면 해당 언어로 답변하세요.
            
            [Context]:
            {context_text}
            """
            
            llm = ChatOllama(model=MODEL_NAME, temperature=0, num_ctx=4096, keep_alive="60m")

            full_messages = [("system", system_prompt)] 
            
            # 최근 10개의 대화 기록만 사용하여 속도 최적화 (Windowing)
            # 프런트엔드에서 전체를 보내도 여기서 잘라서 사용
            recent_history = request.history[-6:] 
            
            for msg in recent_history:
                lc_role = msg.role
                if msg.role == 'assistant':
                    lc_role = 'ai'
                elif msg.role == 'human':
                    lc_role = 'human'
                elif msg.role == 'system':
                    lc_role = 'system'

                full_messages.append((lc_role, msg.content))
            
            full_messages.append(("human", request.question))
            
            async for chunk in llm.astream(full_messages):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            yield "❌ 서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)