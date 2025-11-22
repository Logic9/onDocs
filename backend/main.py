import os
import uuid
import re
import multiprocessing
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from langchain_ollama import ChatOllama
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.cache import InMemoryCache
from langchain.globals import set_llm_cache

from kiwipiepy import Kiwi
from transformers import AutoTokenizer

import onnxruntime as ort
import numpy as np

import pymupdf4llm

# ---------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------

set_llm_cache(InMemoryCache())
UPLOAD_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MODEL_NAME = "gemma3n:e2b"
MAX_CONTEXT_WINDOW = 8192
NUM_CORES = multiprocessing.cpu_count()
NUM_THREADS = max(2, NUM_CORES)

print(f"🚀 System Info: Using {NUM_THREADS} threads. Model: {MODEL_NAME}")

# ---------------------------------------------------------
# 임베딩 & 토크나이저 (ONNX 가속)
# ---------------------------------------------------------

def clean_text(text: str) -> str:
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

class OnnxQuantizedEmbeddings(Embeddings):
    def __init__(self, model_dir: str = "./onnx_emb_model"):
        if not os.path.exists(model_dir):
            print("⚠️ ONNX model not found. Falling back to HuggingFace.")
            from langchain_huggingface import HuggingFaceEmbeddings
            self.fallback = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")
            return

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        sess_options = ort.SessionOptions()
        try: sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        except: pass
        sess_options.intra_op_num_threads = NUM_THREADS

        model_path = os.path.join(model_dir, "model_quantized.onnx")
        if not os.path.exists(model_path): model_path = os.path.join(model_dir, "model.onnx")

        self.session = ort.InferenceSession(model_path, sess_options, providers=["CPUExecutionProvider"])
        self.fallback = None

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if self.fallback: return self.fallback.embed_documents(texts)
        inputs = self.tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="np")
        onnx_inputs = { "input_ids": inputs["input_ids"].astype(np.int64), "attention_mask": inputs["attention_mask"].astype(np.int64) }
        outputs = self.session.run(None, onnx_inputs)
        
        last_hidden_state = outputs[0]
        attention_mask = inputs["attention_mask"]
        input_mask_expanded = np.expand_dims(attention_mask, -1)
        input_mask_expanded = np.broadcast_to(input_mask_expanded, last_hidden_state.shape).astype(float)
        sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
        sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
        embeddings = sum_embeddings / sum_mask
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return (embeddings / np.clip(norm, a_min=1e-9, a_max=None)).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]: return self._embed(texts)
    def embed_query(self, text: str) -> List[float]: return self._embed([text])[0]

try: EMBEDDING_MODEL = OnnxQuantizedEmbeddings()
except: 
    from langchain_huggingface import HuggingFaceEmbeddings
    EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

kiwi = Kiwi()
def korean_tokenizer(text: str) -> List[str]: return [token.form for token in kiwi.tokenize(text)]

# ---------------------------------------------------------
# LLM 설정
# ---------------------------------------------------------

llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0.1,
    num_ctx=MAX_CONTEXT_WINDOW,
    num_thread=NUM_THREADS,
    keep_alive="60m",
    num_predict=2048, 
)

app = FastAPI(title="onDocs AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

vector_store = None
bm25_retriever = None
processing_status = {}
DOC_PAGES = []
DOC_METADATA = {}
RISK_CLAUSES = []

class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, str]] = []

class SearchRequest(BaseModel):
    question: str
    top_k: int = 5

# ---------------------------------------------------------
# 메타데이터 & 독소 조항 로직 (Logic-Free, Regex-Based)
# ---------------------------------------------------------

def extract_metadata(text: str):
    meta = {}
    # 제목
    m_title = re.search(r"(발명의\s*명칭|제\s*목|문서\s*제목|과제명|Title|Subject)\s*[:\-]?\s*(.+)", text)
    if m_title: meta["title"] = m_title.group(2).strip()
    
    # 소유자/조직
    m_org = re.search(r"(출원인|출원자|신청인|주관기관|갑|공급자|Company|Organization)\s*[:\-]?\s*\n?(.+)", text)
    if m_org: 
        raw_org = m_org.group(2).strip()
        clean_org = re.sub(r"^\(\d+\)\s*", "", raw_org)
        clean_org = re.sub(r"^\[\d+\]\s*", "", clean_org)
        meta["organization"] = clean_org

    # 작성자/발명자
    m_author = re.search(r"(발명자|저자|작성자|연구책임자|Inventor|Author)\s*[:\-]?\s*\n?((?:.|\n)+?)(?=\n\s*(?:출원인|대리인|등록|날짜|Date|\(\d{2}\)|요약|ABSTRACT|$))", text)
    if m_author:
        raw_authors = m_author.group(2).strip()
        cleaned_block = re.sub(r"\(\d+\)", "", raw_authors)
        cleaned_block = re.sub(r"\[\d+\]", "", cleaned_block)
        authors_list = [a.strip() for a in re.split(r"[,;\n]", cleaned_block) if a.strip()]
        meta["authors"] = list(dict.fromkeys(authors_list))
    
    # 날짜
    m_date = re.search(r"(작성일|체결일|출원일|Date)\s*[:\-]?\s*(\d{4}[-./년]\s*\d{1,2}[-./월]\s*\d{1,2}일?)", text)
    if not m_date:
        m_date = re.search(r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일|\d{4}-\d{1,2}-\d{1,2})", text[:1000])
    if m_date: 
        date_val = m_date.group(2) if len(m_date.groups()) > 1 else m_date.group(1)
        meta["date"] = date_val.strip()
    
    return meta

# 독소 조항 범용 패턴 및 사고 흐름(Reasoning) 주입
UNIVERSAL_RISK_PATTERNS = [
    {
        "category": "권리 강탈",
        "risk_level": "High",
        "reasoning": "사용자가 기여한 아이디어나 개선사항까지 공급자가 소유하려고 합니다. 통상적으로 개선사항은 기여자에게 귀속되어야 공정합니다.",
        # "개선사항/아이디어" ... "갑/공급자" ... "소유/귀속" 패턴
        "regex": r"(개선|발명|아이디어|2차|저작물|지적재산|노하우).{0,80}(갑|회사|공급자|을).{0,30}(귀속|소유|독점)"
    },
    {
        "category": "불공정 면책",
        "risk_level": "High",
        "reasoning": "공급자의 과실로 발생한 손해(데이터 손실 등)에 대해서도 책임을 지지 않겠다고 명시하고 있습니다.",
        # "간접/특별/부수적 손해" ... "책임지지 않는다" or "데이터 손실" ... "책임 없음"
        "regex": r"(간접|부수|특수|데이터|이익|수익|사업).{0,15}(손해|손실|배상|복구).{0,60}(책임.*(없|지.*않|면제|배제)|배상.*(없|않))"
    },
    {
        "category": "일방적 해지",
        "risk_level": "High",
        "reasoning": "사전 경고나 시정 기회(최고) 없이 즉시 계약을 해지할 수 있는 권한을 공급자만 갖고 있습니다.",
        # "최고 없이" or "즉시" ... "해지"
        "regex": r"(최고\s*없이|통지\s*없이|즉시|임의로|일방적으로).{0,40}(해지|해제|종료|중단)"
    },
    {
        "category": "과도한 위약금/제한",
        "risk_level": "Caution",
        "reasoning": "법정 이율을 초과하는 연체료(월 2% 이상)나 환불 불가 조항이 포함되어 있어 금전적 부담이 큽니다.",
        # 월 2% 이상, 환불 불가
        "regex": r"(월\s*[2-9]%|연\s*(2[4-9]|[3-9]\d)%|환불.*(없|불가|불가능|되지)|반환.*(하지|않))"
    },
    {
        "category": "자동 연장 함정",
        "risk_level": "Caution",
        "reasoning": "계약 종료 의사를 명확히 밝히지 않으면 원하지 않아도 자동으로 계약이 연장될 수 있습니다.",
        "regex": r"(이의|의사|통지).{0,40}(없|안|않).{0,40}(자동|연장|갱신|간주)"
    },
    {
        "category": "불공정 관할",
        "risk_level": "Caution",
        "reasoning": "분쟁 발생 시 공급자의 주소지 관할 법원으로 지정되어 있어, 사용자(을)의 방어권 행사가 불편할 수 있습니다.",
        "regex": r"(관할|법원).{0,50}(갑|본점|회사|공급자).{0,20}(소재지|지정)"
    }
]

def extract_risks(pages):
    risks = []
    for p in pages:
        content = p.get("content", "")
        paragraphs = content.split("\n\n")
        
        for para in paragraphs:
            clean_line = para.strip()
            if len(clean_line) < 10: continue 
            
            matched_categories = []
            
            for pattern in UNIVERSAL_RISK_PATTERNS:
                if re.search(pattern["regex"], clean_line, re.IGNORECASE | re.DOTALL):
                    risks.append({
                        "page_number": p.get("page_number"), 
                        "content": clean_line[:200],
                        "full_content": clean_line,
                        "category": pattern["category"],
                        "risk_level": pattern["risk_level"],
                        "reasoning": pattern["reasoning"]
                    })
                    break
    return risks

# ---------------------------------------------------------
# 문서 처리 파이프라인
# ---------------------------------------------------------

def process_document(file_path, file_ext, filename):
    global vector_store, bm25_retriever, processing_status, DOC_PAGES, RISK_CLAUSES, DOC_METADATA
    try:
        processing_status[filename] = "processing"
        docs = []
        if file_ext == ".pdf":
            data = pymupdf4llm.to_markdown(file_path, page_chunks=True)
            DOC_PAGES = [{"page_number": d["metadata"]["page"], "content": clean_text(d["text"])} for d in data]
            for p in DOC_PAGES:
                docs.append(Document(page_content=p["content"], metadata={"page_number": p["page_number"]}))
        else:
            with open(file_path, "r", encoding="utf-8") as f: text = clean_text(f.read())
            DOC_PAGES = [{"page_number": 1, "content": text}]
            docs = [Document(page_content=text, metadata={"page_number": 1})]

        # 메타데이터 추출 (앞부분 3000자)
        header_text = DOC_PAGES[0]["content"] if DOC_PAGES else ""
        if len(DOC_PAGES) > 1: header_text += "\n" + DOC_PAGES[1]["content"]
        DOC_METADATA = extract_metadata(header_text[:3000])
        
        # 독소 조항 추출 및 캐싱
        RISK_CLAUSES = extract_risks(DOC_PAGES)

        # RAG 인덱싱
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        splits = splitter.split_documents(docs)

        vector_store = FAISS.from_documents(splits, EMBEDDING_MODEL)
        bm25_retriever = BM25Retriever.from_documents(splits, preprocess_func=korean_tokenizer)
        bm25_retriever.k = 10 

        processing_status[filename] = "completed"
        print(f"✅ Processed: {filename}")
        print(f"⚠️ Risks Found: {len(RISK_CLAUSES)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        processing_status[filename] = "failed"

# ---------------------------------------------------------
# API 엔드포인트
# ---------------------------------------------------------

@app.get("/status/{filename}")
def status(filename: str): return {"status": processing_status.get(filename, "unknown")}

@app.post("/upload")
async def upload(bg_tasks: BackgroundTasks, file: UploadFile = File(...)):
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(path, "wb") as buffer: 
        import shutil
        shutil.copyfileobj(file.file, buffer)
    bg_tasks.add_task(process_document, path, os.path.splitext(file.filename)[1].lower(), file.filename)
    return {"message": "ok"}

@app.get("/document/pages")
def pages(): return {"pages": DOC_PAGES}

@app.get("/risks")
def risks(): return {"results": RISK_CLAUSES}

@app.post("/search")
async def search(req: SearchRequest):
    if not vector_store: return {"results": []}
    faiss = vector_store.as_retriever(search_kwargs={"k": req.top_k})
    ensemble = EnsembleRetriever(retrievers=[bm25_retriever, faiss], weights=[0.5, 0.5])
    docs = await ensemble.ainvoke(req.question)
    return {"results": [{"page_number": d.metadata.get("page_number"), "content": d.page_content} for d in docs]}

@app.post("/chat")
async def chat(req: ChatRequest):
    async def gen():
        if not vector_store: 
            yield "문서를 분석 중이거나 아직 업로드되지 않았습니다."
            return

        q = req.question
        risk_keywords = ["독소", "조항", "위험", "주의", "유리", "불리", "문제", "제약", "의무", "책임", "risk", "toxic"]
        is_risk_query = any(k in q for k in risk_keywords)

        summary_keywords = ["요약", "정리", "알려줘", "설명", "내용", "뭐야", "summary", "explain", "overview", "주요"]
        is_summary_query = any(k in q for k in summary_keywords) and not is_risk_query

        meta_context = ""
        if DOC_METADATA:
            meta_context = (
                f"[문서 기본 정보]\n"
                f"- 제목: {DOC_METADATA.get('title', '제목 미상')}\n"
                f"- 조직/주체: {DOC_METADATA.get('organization', '정보 없음')}\n"
                f"- 날짜: {DOC_METADATA.get('date', '정보 없음')}\n"
            )

        risk_context = ""
        if RISK_CLAUSES:
            if is_risk_query:
                risk_context = "\n[⚠️ 상세 위험 분석]\n"
                for r in RISK_CLAUSES[:5]:
                    risk_context += f"- (P.{r['page_number']}) [{r['category']}]: {r['reasoning']}\n"
            elif is_summary_query:
                risk_context = "\n[⚠️ 문서 특이사항 요약]\n"
                categories = set([r['category'] for r in RISK_CLAUSES])
                risk_context += f"- 탐지된 주요 제약 사항: {', '.join(categories)}\n"
            else:
                risk_context = ""

        # 모드별 지침
        
        base_instruction = "당신은 문서를 분석하고 친절하게 답변하는 AI 비서 'onDocs'입니다."

        if is_summary_query:
            specific_instruction = """
[답변 작성 가이드: 요약 모드]
사용자가 문서 내용을 파악하고자 합니다. 아래 **3가지 목차**에 맞춰 답변을 작성하세요:

1. **문서 개요**: 이 문서의 종류와 목적, 작성 주체를 1~2문장으로 자연스럽게 설명.
2. **주요 내용**: 핵심 내용을 **글머리 기호(Bullet points)**로 3~5가지 정리.
3. **특이 사항**: [⚠️ 문서 특이사항 요약]에 내용이 있다면 "주의할 점"으로 짧게 언급 (없으면 생략).

[작성 태도]
- 톤앤매너에 대한 메타 설명(예: "전문적으로 씁니다")은 출력하지 마세요.
- "~입니다", "~로 요약됩니다" 등 정중한 어미를 사용하세요.
"""
        elif is_risk_query:
            specific_instruction = """
[답변 작성 가이드: 위험 분석 모드]
사용자가 위험 요소를 묻고 있습니다. [⚠️ 상세 위험 분석] 데이터를 인용하여 설명하세요:
1. 문제 조항과 페이지 번호 명시.
2. 사용자에게 불리한 이유 설명.
3. "~하므로 주의가 필요합니다"와 같이 정중하게 조언하는 어조 사용.
"""
        else:
            specific_instruction = """
[답변 작성 가이드: 일반/팩트 확인 모드]
1. **친절한 답변**: 질문에 대한 정보를 명확하게 제공하되, 단답형보다는 완전한 문장("~입니다", "~로 확인됩니다")으로 답하세요.
2. **문맥 유지**: 답변에 필요한 부가 정보가 있다면 자연스럽게 덧붙여도 좋습니다.
3. **제약 사항**: 질문과 직접 관련이 없는 '독소 조항'이나 '위험 요소'에 대한 언급은 **절대 하지 마세요**.
"""

        # RAG 검색
        faiss = vector_store.as_retriever(search_kwargs={"k": 6})
        ensemble = EnsembleRetriever(retrievers=[bm25_retriever, faiss], weights=[0.5, 0.5])
        
        docs = await ensemble.ainvoke(req.question)
        final_docs = docs[:5] 
        final_docs.sort(key=lambda x: x.metadata.get("page_number", 0))
        doc_context = "\n\n".join([f"[Page {d.metadata.get('page_number')}]: {d.page_content}" for d in final_docs])

        prompt = f"""system
{base_instruction}

{specific_instruction}

user
{meta_context}

{risk_context}

[참고 자료]
{doc_context}

[질문]
{req.question}

model
"""
        async for chunk in llm.astream(prompt):
            if chunk.content: yield chunk.content

    return StreamingResponse(gen(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)