# onDocs · archive/zip-original

로컬에서 발견한 별도 구현·이전 버전의 소스 스냅샷입니다. 원본 폴더는 보존하고 비밀값·사용자 데이터·의존성 사본·대용량 모델을 제외했습니다.

현재 대표 설명과 브랜치 관계는 [기본 브랜치 README](https://github.com/Logic9/onDocs/blob/main/README.md)를 참고하세요.

## 이 버전의 구성

| 경로 | 역할 / 실행 정보 |
| --- | --- |
| `.gitignore` | 보관한 원본 구성 |
| `README.md` | 보관한 원본 구성 |
| `backend/` | 보관한 원본 구성 |
| `docs/` | 보관한 원본 구성 |
| `frontend/` | 보관한 원본 구성 |

## 패키지에 선언된 명령

아래 명령은 원본 manifest 기준입니다. 실행·배포 성공을 검증했다는 의미는 아니며, 해당 폴더에서 의존성과 외부 설정을 먼저 준비해야 합니다.

### `frontend/package.json`

- `npm run dev` → `next dev`
- `npm run build` → `next build`
- `npm run start` → `next start`
- `npm run lint` → `eslint`


소스 출처와 비교 관계는 [정리 기록](docs/SOURCE_MAP.md)에 있습니다. 하드코딩 비밀값의 `REPLACE_WITH_LOCAL_SECRET` 표시는 실행 전에 로컬 설정으로 연결해야 합니다.
