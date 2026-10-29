# onDocs — 문서 근거 기반 분석·대화

PDF를 올리면 내용을 검색하고 근거 페이지를 보며 질문할 수 있습니다. 위험 항목을 모아보고 원문과 대조합니다.

## 주요 기능

- PDF 업로드·백그라운드 처리와 상태 확인
- 페이지별 문서 뷰어, Markdown 표시와 근거 페이지 이동
- 위험 항목 대시보드와 문서 검색
- 문서 기반 채팅과 스트리밍 응답

| 위치 | 역할 |
| --- | --- |
| `frontend/app/` | Next.js 화면 진입점 |
| `frontend/components/features/` | 뷰어·채팅·분석 UI |
| `frontend/hooks/` | 파일 처리·채팅 상태 |
| `frontend/utils/api.js` | 백엔드 호출 |
| `backend/main.py` | 업로드·문서 처리·검색·대화 FastAPI |
| `backend/export_onnx.py` | 임베딩 모델 ONNX 변환 |
| `backend/requirements.txt` | Python 의존성 |
| `docs/` | 프로젝트 보조 문서 |

백엔드는 PDF 처리, 한국어 토큰화, BM25·벡터 검색, FAISS·ONNX 임베딩과 로컬 모델 연동 코드를 포함합니다. 대표 API는 `/upload`, `/status/{filename}`, `/document/pages`, `/risks`, `/search`, `/chat`입니다.

## 실행 준비

백엔드와 프런트엔드를 각각 실행합니다.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

모델 서비스·모델 이름·ONNX 자산 경로와 프런트엔드 API 주소를 실제 코드에 맞춰 준비해야 합니다. 생성 모델과 임베딩 가중치는 별도 자산이며 소스만으로 자동 제공된다고 보장하지 않습니다. OS·Python·Torch 버전의 호환성도 확인하세요.

## 브랜치와 데이터

기본 브랜치는 기존 GitHub 구현입니다. 로컬의 변경 소스는 `archive/local-logic9`, 다른 오프라인 대응 스냅샷은 `archive/offline`, ZIP에만 남아 있던 다른 백엔드 구현은 `archive/zip-original` 브랜치로 보관합니다. 가까운 사본을 중복 디렉터리·저장소로 만들지 않았습니다.

업로드 문서·검색 인덱스·모델 가중치·가상환경·실제 비밀값은 코드와 분리합니다. 답변·위험 추출은 모델 결과이므로 원문 근거를 직접 확인해야 합니다. 인증·문서별 접근 격리·삭제·처리량 제한은 공개 서비스 운영 전에 별도로 검증해야 합니다.

소스 출처·보관 브랜치·제외 범위는 [정리 기록](docs/SOURCE_MAP.md)에 있습니다.
