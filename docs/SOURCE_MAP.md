# 소스 출처와 버전 보존

2026-10-29에 Logic9 작업 폴더와 기존 GitHub 기본 브랜치를 비교해 정리했습니다. 원본 로컬 파일은 변경하지 않았습니다. 같은 프로젝트의 사본은 별도 저장소로 반복 생성하지 않고 Git 브랜치로 구분합니다.

| 브랜치 / 경로 | 원본 프로젝트 묶음 | 관계 |
| --- | --- | --- |
| `archive/local-logic9` · `/` | 01_창업_서비스기획/onDocs/개발프로젝트/onDocs-main | 선택한 원본 소스 |
| `archive/offline` · `frontend` | 01_창업_서비스기획/onDocs/개발프로젝트/onDocs-good/frontend | 9 changed files vs main frontend; do not treat as exact duplicate |
| `archive/offline` · `backend` | 01_창업_서비스기획/onDocs/개발프로젝트/onDocs-good/backend | 4 changed files; offline backend |

## 업로드 범위

소스, 필요한 가벼운 실행 자산, 의존성 선언과 기존 라이선스·출처를 보존합니다. 가상환경·캐시·설치 파일·실제 환경변수 파일·비밀키·사용자 DB·로그·쿠키·대용량 학습 모델·원본 녹음은 제외합니다. 샘플 스키마와 마이그레이션은 실제 데이터 백업과 구분합니다.

인식 가능한 하드코딩 비밀값은 `REPLACE_WITH_LOCAL_SECRET`로 치환했습니다. 해당 위치는 실행 전에 로컬 설정으로 연결해야 합니다. 이 정리는 제품의 실행·배포 성공이나 보안 인증을 보장하지 않습니다.

기존 저장소의 커밋 이력은 유지했습니다. 과거에 커밋된 비밀값은 현재 파일에서 제외해도 이전 이력에 남을 수 있으므로, 해당 서비스에서 기존 키 폐기·재발급이 필요합니다.
