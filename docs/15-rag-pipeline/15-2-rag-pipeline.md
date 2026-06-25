---
title: "15-2. 적재 → 청킹 → 임베딩 → 검색 → 생성"
order: 2
tags: [rag, pipeline, implementation, langchain]
status: draft
author: vivace
---

# 15-2. 적재 → 청킹 → 임베딩 → 검색 → 생성

사내 문서 기반 Q&A 봇을 처음부터 끝까지 만들어봅니다.

---

## 완성된 RAG 파이프라인 구현

```python
# rag_pipeline.py
import os
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 설정
DOCS_DIR = "./docs"
CHROMA_DIR = "./chroma_db"
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 5

embedding_fn = OpenAIEmbeddings(model=EMBEDDING_MODEL)


# ─── 1. 인덱싱 파이프라인 ───

def index_documents(docs_dir: str = DOCS_DIR) -> Chroma:
    print("문서 로드 중...")
    loader = DirectoryLoader(
        docs_dir,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True
    )
    raw_docs = loader.load()
    print(f"  → {len(raw_docs)}개 페이지 로드됨")

    print("청킹 중...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(raw_docs)
    print(f"  → {len(chunks)}개 청크 생성됨")

    print("임베딩 및 저장 중...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_fn,
        persist_directory=CHROMA_DIR
    )
    print(f"  → Vector DB 저장 완료: {CHROMA_DIR}")
    return vectorstore


def load_vectorstore() -> Chroma:
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embedding_fn
    )


# ─── 2. 쿼리 파이프라인 ───

SYSTEM_PROMPT = """당신은 사내 문서를 기반으로 답하는 어시스턴트입니다.

규칙:
- 반드시 제공된 [참고 문서]만을 근거로 답하세요
- 문서에 없는 내용은 "제공된 문서에서 찾을 수 없습니다"라고 답하세요
- 답변 끝에 [출처: 문서 n] 형식으로 근거를 표시하세요"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("user", """[참고 문서]
{context}

[질문]
{question}""")
])

def format_docs(docs) -> str:
    return "\n\n---\n\n".join(
        f"[문서 {i+1}] (출처: {doc.metadata.get('source', '?')})\n{doc.page_content}"
        for i, doc in enumerate(docs)
    )

def build_rag_chain(vectorstore: Chroma):
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K}
    )
    
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0)
    
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


# ─── 실행 ───

if __name__ == "__main__":
    # 최초 실행: 인덱싱
    if not Path(CHROMA_DIR).exists():
        vectorstore = index_documents()
    else:
        vectorstore = load_vectorstore()
        print(f"기존 Vector DB 로드: {vectorstore._collection.count()}개 청크")
    
    chain = build_rag_chain(vectorstore)
    
    print("\nRAG Q&A 봇 시작 (종료: q)")
    while True:
        question = input("\n질문: ").strip()
        if question.lower() == 'q':
            break
        if not question:
            continue
        
        print("\n답변:")
        for chunk in chain.stream(question):
            print(chunk, end="", flush=True)
        print()
```

---

## FastAPI로 서빙

```python
# api.py
from fastapi import FastAPI
from pydantic import BaseModel
from rag_pipeline import load_vectorstore, build_rag_chain

app = FastAPI(title="RAG Q&A API")

vectorstore = load_vectorstore()
chain = build_rag_chain(vectorstore)

class QuestionRequest(BaseModel):
    question: str
    session_id: str | None = None

class AnswerResponse(BaseModel):
    answer: str
    question: str

@app.get("/health")
def health():
    doc_count = vectorstore._collection.count()
    return {"status": "ok", "indexed_chunks": doc_count}

@app.post("/ask", response_model=AnswerResponse)
def ask(request: QuestionRequest):
    answer = chain.invoke(request.question)
    return AnswerResponse(answer=answer, question=request.question)

@app.post("/index")
def trigger_reindex():
    """새 문서를 추가했을 때 재인덱싱 트리거"""
    from rag_pipeline import index_documents
    global vectorstore, chain
    vectorstore = index_documents()
    chain = build_rag_chain(vectorstore)
    return {"status": "reindexed", "chunks": vectorstore._collection.count()}
```

---

## 증분 업데이트 — 문서 변경 감지

```python
import hashlib
import json
from pathlib import Path

HASH_STORE = ".doc_hashes.json"

def get_file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def find_changed_docs(docs_dir: str) -> tuple[list[str], list[str]]:
    """반환: (새로 추가/수정된 파일, 삭제된 파일)"""
    current_hashes = {
        str(p): get_file_hash(str(p))
        for p in Path(docs_dir).rglob("*.pdf")
    }
    
    if Path(HASH_STORE).exists():
        with open(HASH_STORE) as f:
            stored_hashes = json.load(f)
    else:
        stored_hashes = {}
    
    added_or_modified = [
        path for path, h in current_hashes.items()
        if stored_hashes.get(path) != h
    ]
    deleted = [path for path in stored_hashes if path not in current_hashes]
    
    # 해시 업데이트
    with open(HASH_STORE, "w") as f:
        json.dump(current_hashes, f)
    
    return added_or_modified, deleted

def incremental_index(vectorstore: Chroma, docs_dir: str):
    added, deleted = find_changed_docs(docs_dir)
    
    if deleted:
        # 삭제된 문서의 청크 제거
        vectorstore.delete(where={"source": {"$in": deleted}})
        print(f"삭제된 문서 {len(deleted)}개의 청크 제거")
    
    if added:
        # 수정/추가된 문서 재인덱싱
        for path in added:
            vectorstore.delete(where={"source": path})  # 기존 청크 제거
        
        loader = DirectoryLoader(".", glob=added)  # 변경된 파일만
        # ... 청킹 및 임베딩 추가
        print(f"업데이트된 문서 {len(added)}개 재인덱싱")
```

---

> RAG는 한 번 만들고 끝이 아닙니다. 문서가 바뀌면 인덱스도 바뀌어야 합니다. 증분 업데이트 전략을 처음부터 설계하세요.
