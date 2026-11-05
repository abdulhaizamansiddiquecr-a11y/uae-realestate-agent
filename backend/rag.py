import json
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()
client = genai.Client()

EMBED_MODEL = "gemini-embedding-001"
BASE = Path(__file__).parent
KNOWLEDGE_DIR = BASE / "knowledge"
INDEX_FILE = BASE / "knowledge_index.json"


def embed(texts):
    """Turns a list of texts into a list of number-lists. Retries if busy."""
    for attempt in range(5):
        try:
            result = client.models.embed_content(model=EMBED_MODEL, contents=texts)
            return [e.values for e in result.embeddings]
        except errors.APIError as e:
            if e.code in (429, 500, 503):
                wait = 5 * (attempt + 1)
                print(f"(Google is busy, trying again in {wait} seconds...)")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Google is too busy right now. Try again in a minute.")


def make_chunks():
    """Cuts every .md file into pieces, one piece per '## ' section."""
    chunks = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text()
        title = text.split("\n")[0].replace("# ", "").strip()
        for section in text.split("\n## ")[1:]:
            heading, _, body = section.partition("\n")
            chunks.append(
                {
                    "source": path.name,
                    "text": f"{title} - {heading.strip()}\n{body.strip()}",
                }
            )
    return chunks


def build_index():
    """Reads the knowledge folder and saves chunks + embeddings to a file."""
    chunks = make_chunks()
    print(f"Found {len(chunks)} pieces. Creating embeddings...")
    vectors = embed([c["text"] for c in chunks])
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    INDEX_FILE.write_text(json.dumps(chunks))
    print(f"Saved the index to {INDEX_FILE.name}")


_index = None


def search_knowledge(question: str) -> list[dict]:
    """Search the knowledge base for renting rules, checklists and notes.
    Use this for questions about Ejari, security deposits, rent increases,
    eviction, disputes, what to check before renting, or about the data itself.

    Args:
        question: The question to look up, written as a short sentence.
    """
    global _index
    if _index is None:
        _index = json.loads(INDEX_FILE.read_text())

    q = np.array(embed([question])[0])
    scored = []
    for chunk in _index:
        v = np.array(chunk["embedding"])
        score = float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v)))
        scored.append((score, chunk))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {"source": c["source"], "score": round(s, 3), "text": c["text"]}
        for s, c in scored[:3]
    ]


if __name__ == "__main__":
    build_index()
    print("\nTest search: 'how much security deposit do I pay in Dubai?'\n")
    for r in search_knowledge("how much security deposit do I pay in Dubai?"):
        print(r["score"], r["source"])
        print(r["text"][:150], "...\n")