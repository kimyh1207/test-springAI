#!/usr/bin/env python3
"""
WikiDocs 자동 발행 스크립트

동작:
1. docs/ 폴더의 모든 마크다운 파일을 순회
2. YAML 프론트매터에서 wikidocs_id와 status를 읽음
3. status가 'published'인 파일을 WikiDocs API로 발행/갱신
4. 발행 후 wikidocs_id를 파일에 기록

환경변수:
  WIKIDOCS_TOKEN: WikiDocs API 토큰
"""

import os
import re
import sys
import requests
from pathlib import Path

try:
    import yaml
except ImportError:
    print("pyyaml이 필요합니다: pip install pyyaml")
    sys.exit(1)

WIKIDOCS_API = "https://wikidocs.net/api/v1"
TOKEN = os.environ.get("WIKIDOCS_TOKEN", "")

if not TOKEN:
    print("WIKIDOCS_TOKEN 환경변수가 설정되지 않았습니다.")
    sys.exit(1)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """YAML 프론트매터와 본문을 분리"""
    match = re.match(r"^---\n(.+?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    meta = yaml.safe_load(match.group(1))
    body = match.group(2).strip()
    return meta, body


def publish_page(title: str, content: str, book_id: str, page_id: str = "") -> str:
    """WikiDocs 페이지 생성 또는 갱신. 페이지 ID를 반환"""
    headers = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

    if page_id:
        url = f"{WIKIDOCS_API}/page/{page_id}/"
        resp = requests.patch(url, json={"title": title, "content": content}, headers=headers)
    else:
        url = f"{WIKIDOCS_API}/page/"
        resp = requests.post(url, json={"title": title, "content": content, "book": book_id}, headers=headers)

    resp.raise_for_status()
    return str(resp.json().get("id", ""))


def main():
    docs_root = Path("docs")
    # WikiDocs 책 ID는 환경변수나 설정 파일에서 가져옴
    book_id = os.environ.get("WIKIDOCS_BOOK_ID", "")

    for md_file in sorted(docs_root.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)

        if not meta or meta.get("status") != "published":
            continue

        title = meta.get("title", md_file.stem)
        page_id = meta.get("wikidocs_id", "")

        print(f"발행 중: {title}")
        try:
            new_id = publish_page(title, body, book_id, page_id)
            if not page_id:
                # 새로 발행된 경우 ID를 파일에 기록
                new_content = content.replace(
                    'wikidocs_id: ""', f'wikidocs_id: "{new_id}"'
                )
                md_file.write_text(new_content, encoding="utf-8")
            print(f"  완료: page_id={new_id}")
        except requests.HTTPError as e:
            print(f"  오류: {e}")


if __name__ == "__main__":
    main()
