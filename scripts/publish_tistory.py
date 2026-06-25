#!/usr/bin/env python3
"""
Tistory 자동 포스팅 스크립트

동작:
1. docs/ 폴더의 변경된 마크다운 파일을 찾음
2. status가 'published'인 파일을 Tistory API로 발행
3. 발행 후 tistory_id를 파일에 기록

환경변수:
  TISTORY_ACCESS_TOKEN: Tistory OAuth 액세스 토큰
  TISTORY_BLOG_NAME: 블로그 이름 (예: myblog)
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

TISTORY_API = "https://www.tistory.com/apis"
ACCESS_TOKEN = os.environ.get("TISTORY_ACCESS_TOKEN", "")
BLOG_NAME = os.environ.get("TISTORY_BLOG_NAME", "")

if not ACCESS_TOKEN or not BLOG_NAME:
    print("TISTORY_ACCESS_TOKEN, TISTORY_BLOG_NAME 환경변수가 필요합니다.")
    sys.exit(1)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.+?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    meta = yaml.safe_load(match.group(1))
    body = match.group(2).strip()
    return meta, body


def get_changed_files() -> list[Path]:
    """git diff로 변경된 docs/*.md 파일 목록을 가져옴"""
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", "docs/**/*.md"],
        capture_output=True, text=True
    )
    return [Path(p) for p in result.stdout.strip().splitlines() if p.endswith(".md")]


def publish_post(title: str, content: str, tags: list, post_id: str = "") -> str:
    """Tistory 포스트 작성 또는 수정. post_id를 반환"""
    endpoint = f"{TISTORY_API}/post/{'modify' if post_id else 'write'}"
    params = {
        "access_token": ACCESS_TOKEN,
        "output": "json",
        "blogName": BLOG_NAME,
        "title": title,
        "content": content,
        "visibility": "3",  # 공개
        "tag": ",".join(tags[:10]),  # Tistory 태그 최대 10개
    }
    if post_id:
        params["postId"] = post_id

    resp = requests.post(endpoint, data=params)
    resp.raise_for_status()
    data = resp.json()
    return str(data.get("tistory", {}).get("postId", ""))


def main():
    changed = get_changed_files()
    if not changed:
        # 변경 파일이 없으면 전체 스캔 (첫 실행 대비)
        changed = list(Path("docs").rglob("*.md"))

    for md_file in changed:
        if not md_file.exists():
            continue
        content = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)

        if not meta or meta.get("status") != "published":
            continue

        title = meta.get("title", md_file.stem)
        tags = meta.get("tags", [])
        post_id = meta.get("tistory_id", "")

        print(f"Tistory 발행 중: {title}")
        try:
            new_id = publish_post(title, body, tags, post_id)
            if not post_id:
                new_content = content.replace(
                    'tistory_id: ""', f'tistory_id: "{new_id}"'
                )
                md_file.write_text(new_content, encoding="utf-8")
            print(f"  완료: post_id={new_id}")
        except requests.HTTPError as e:
            print(f"  오류: {e}")


if __name__ == "__main__":
    main()
