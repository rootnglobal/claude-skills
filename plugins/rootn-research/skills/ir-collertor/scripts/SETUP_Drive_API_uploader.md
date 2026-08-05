# Drive API 업로더 셋업 가이드 (drive_uploader.py)

ir-collertor가 대용량 IR PDF까지 Drive에 **자동·무손실** 업로드하도록 만드는 코드 경로.
Drive 웹의 네이티브 파일 피커, 커넥터의 base64 인라인 한계를 둘 다 우회한다.
multipart/resumable 업로드 + md5 검증.

> 실행 위치: **사용자 로컬 PC**(브라우저 OAuth 동의가 필요). 업로드할 PDF도 로컬에 있으니 자연스럽다.

---

## 1. Google Cloud OAuth 클라이언트 만들기 (최초 1회, ~5분)

1. https://console.cloud.google.com → 프로젝트 생성(또는 기존 선택).
2. **APIs & Services > Library** → "Google Drive API" 검색 → **Enable**.
3. **APIs & Services > OAuth consent screen**:
   - User Type: **External**(개인 Gmail) 또는 Internal(워크스페이스).
   - 앱 이름 아무거나(예: RootN IR Uploader), 본인 이메일 입력, 저장.
   - **Test users**에 본인 Gmail 계정을 추가(External일 때 필수).
4. **APIs & Services > Credentials > + Create Credentials > OAuth client ID**:
   - Application type: **Desktop app** → Create.
   - 생성된 클라이언트의 **JSON 다운로드** → 파일명을 `credentials.json`으로.

## 2. 파일 배치 & 설치

`drive_uploader.py`, `credentials.json`, 업로드할 PDF들을 **같은 폴더**에 둔다.

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## 3. 최초 인가 (1회) + 업로드 실행

아래를 그 폴더에서 실행. 처음 실행하면 브라우저가 열리며 동의 → 이후 `token.json`이 캐시되어 재인가 불필요.

```bash
# SUMCO IR 2건 → Wafer/Sumco 폴더
python drive_uploader.py --folder 1ejl6F2qmjqvPHvKf6esMI2WqAP9ppFOS \
  SUMCO_Presentation_Q1_FY2026.pdf SUMCO_Consolidated_Results_Q1_FY2026.pdf

# Shin-Etsu Q&A → Wafer/Shin-etsu 폴더
python drive_uploader.py --folder 1XJ1f6S545rjSbQvMWU0_5AKB1Du5q_4j \
  ShinEtsu_QA_Summary_Q4FY2025_20260428.pdf
```

출력 예: `id=... size=840,878 [OK] md5=[OK] modified=... 검증 OK`.
size·md5가 모두 OK면 무손실 업로드 확정.

> 덮어쓰기 방지가 필요하면 `--name-suffix _v2` 추가.

## 4. ir-collertor 연동

스킬의 Step 4(드라이브 업로드)에서 Chrome UI 대신 이 스크립트를 호출하도록 바꾼다.
(스킬 패치 문구는 `ir-collertor_skill_patch.md` 참조 → 다음 대화형 세션에서 skill-release로 반영.)

## 5. 참고 폴더 ID (Wafer)

| 폴더 | ID |
|---|---|
| Wafer/Sumco | 1ejl6F2qmjqvPHvKf6esMI2WqAP9ppFOS |
| Wafer/Shin-etsu | 1XJ1f6S545rjSbQvMWU0_5AKB1Du5q_4j |
| Wafer(루트) | 1-ZUubq07lQZ5cN8DLIzZi-Zx5hxxvBZm |

(폴더 ID는 Drive에서 폴더 연 뒤 URL의 `/folders/` 뒤 문자열)

## 6. 판단 포인트 (택1)

- **인증 방식:** *OAuth Desktop*(권장, 본인 My Drive에 그대로 업로드) vs *Service Account*(무인 자동화 가능하나 개인 My Drive 폴더는 SA에 공유해야 하고 파일 소유자가 SA가 됨). 개인 Drive 폴더(Wafer 등)에 올리는 지금 용도는 OAuth Desktop이 맞다.
- **스코프:** 기본 `drive.file`(앱이 만든 파일만 접근, 프라이버시 우선). 기존 폴더 업로드에서 403이 나면 스크립트 상단 SCOPES를 `https://www.googleapis.com/auth/drive`(전체)로 바꾸고 token.json 삭제 후 재인가.

## 7. 트러블슈팅

- `access_blocked`: OAuth consent screen의 Test users에 본인 계정 미등록. 등록 후 재시도.
- `403 insufficientFilePermissions` / 폴더 접근 불가: 스코프를 전체(`drive`)로 변경(§6).
- `token.json` 만료/스코프 변경: `token.json` 삭제 후 재실행하여 재인가.
- 공유 드라이브(팀 드라이브)면 `--folder`에 공유드라이브 폴더 ID 사용(스크립트는 supportsAllDrives=True 이미 적용).
