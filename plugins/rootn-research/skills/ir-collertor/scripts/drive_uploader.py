#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drive_uploader.py — Google Drive API 업로더 (ir-collertor 보조 도구)

목적:
  로컬 파일을 Drive에 multipart/resumable 방식으로 업로드한다.
  → 대용량(수 MB) PDF도 OK. 'base64 인라인 한계'와 'Drive 웹 네이티브 파일 피커'
    두 문제를 모두 우회한다.

특징:
  - OAuth Desktop 플로우: 최초 1회만 브라우저에서 인가 → token.json 캐시 후 재사용.
    (token.json 이 생기면 이후에는 브라우저 없이 자동 실행 가능 = 미래 자동화의 핵심)
  - 3점 검증: 업로드 후 Drive가 돌려주는 size·md5Checksum·modifiedTime을 로컬과 대조.
  - 덮어쓰기 대신 --name-suffix 로 새 파일명(_v2 등) 부여 가능.

사용:
  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

  # (1) 최초 인가만 하고 싶을 때 (파일 업로드 없이 token.json 만 생성):
  python drive_uploader.py --auth-only

  # (2) 실제 업로드:
  python drive_uploader.py --folder <FOLDER_ID> [--name-suffix _v2] file1.pdf file2.pdf ...

사전 준비:
  이 스크립트와 같은 폴더에 credentials.json (Google Cloud > OAuth 'Desktop app' 클라이언트).
"""
import argparse
import hashlib
import os
import sys

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# drive.file = 이 앱이 생성/연 파일만 접근(프라이버시 우선). 폴더 ID를 알면 그 폴더에 새 파일 생성 가능.
# 기존 폴더 업로드에서 403이 나면 아래를 전체 권한으로 바꾸고 token.json 삭제 후 재인가:
#   SCOPES = ["https://www.googleapis.com/auth/drive"]
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

HERE = os.path.dirname(os.path.abspath(__file__))
CRED = os.path.join(HERE, "credentials.json")
TOKEN = os.path.join(HERE, "token.json")


def get_service():
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CRED):
                sys.exit(f"[ERR] credentials.json 없음: {CRED}\n"
                         f"      OAuth 'Desktop app' 클라이언트 JSON을 이 경로에 두세요.")
            flow = InstalledAppFlow.from_client_secrets_file(CRED, SCOPES)
            creds = flow.run_local_server(port=0)  # 브라우저 동의 → 콜백 수신
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_one(svc, path, folder_id, name):
    meta = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(path, resumable=True, chunksize=5 * 1024 * 1024)
    req = svc.files().create(
        body=meta, media_body=media,
        fields="id,name,size,md5Checksum,modifiedTime,webViewLink",
        supportsAllDrives=True,
    )
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"    ...{int(status.progress() * 100)}%")
    return resp


def main():
    ap = argparse.ArgumentParser(description="Google Drive API 업로더")
    ap.add_argument("--folder", help="대상 Drive 폴더 ID (업로드 시 필수)")
    ap.add_argument("--name-suffix", default="", help="파일명 접미사(예: _v2). 덮어쓰기 방지용")
    ap.add_argument("--auth-only", action="store_true",
                    help="업로드 없이 최초 인가만 수행하여 token.json 생성(향후 자동화용)")
    ap.add_argument("files", nargs="*", help="업로드할 로컬 파일 경로들")
    a = ap.parse_args()

    svc = get_service()  # 최초 실행 시 브라우저 인가 → token.json 캐시

    if a.auth_only:
        print(f"[OK] 인가 완료. 토큰 저장됨: {TOKEN}")
        print("     이제 credentials.json + token.json 이 있으면 브라우저 없이 자동 업로드 가능합니다.")
        return

    if not a.folder or not a.files:
        sys.exit("[ERR] 업로드하려면 --folder <ID> 와 파일 경로가 필요합니다. "
                 "(인가만 하려면: python drive_uploader.py --auth-only)")

    passed = 0
    for p in a.files:
        if not os.path.exists(p):
            print(f"[SKIP] 파일 없음: {p}")
            continue
        local_size = os.path.getsize(p)
        local_md5 = md5_of(p)
        base, ext = os.path.splitext(os.path.basename(p))
        name = f"{base}{a.name_suffix}{ext}"
        print(f"[UP] {name}  ({local_size:,} B)  → folder {a.folder}")
        r = upload_one(svc, p, a.folder, name)

        rsize = int(r.get("size", 0))
        rmd5 = r.get("md5Checksum", "")
        size_ok = (rsize == local_size)
        md5_ok = (rmd5 == local_md5) if rmd5 else None
        verdict = "OK" if (size_ok and md5_ok is not False) else "FAIL"
        print(f"     id={r.get('id')}  size={rsize:,} [{'OK' if size_ok else 'MISMATCH'}]  "
              f"md5=[{'OK' if md5_ok else ('n/a' if md5_ok is None else 'MISMATCH')}]  "
              f"modified={r.get('modifiedTime')}")
        print(f"     link={r.get('webViewLink')}   → 검증 {verdict}")
        if verdict == "OK":
            passed += 1
        else:
            print("     ⚠ 검증 실패 — --name-suffix 로 재업로드 후 이전본 수동 삭제 권장")

    print(f"\n완료: {passed}/{len(a.files)} 검증 통과")


if __name__ == "__main__":
    main()
