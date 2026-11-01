
import os
import requests

OLLAMA_URL = "http://localhost:11434"

# Replace with the exact tags returned by ollama list.
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.getenv(
    "EMBED_MODEL",
    "nomic-embed-text:latest"
)


def test_qwen():
    print("\n1. Testing Qwen inference...")

    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": QWEN_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "A frontend service depends on payment, "
                        "which depends on inventory-db. "
                        "The database connection pool is exhausted. "
                        "Explain the failure propagation in 3 sentences."
                    )
                }
            ],
            "stream": False,
            "keep_alive": 0,
            "options": {
                "temperature": 0.1
            }
        },
        timeout=180
    )

    response.raise_for_status()

    answer = response.json()["message"]["content"]

    print("\nQWEN RESPONSE:")
    print(answer)

    assert answer.strip(), "Qwen returned an empty response"

    print("\nQwen inference: SUCCESS")


def test_embeddings():
    print("\n2. Testing Nomic embeddings...")

    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": EMBED_MODEL,
            "input": [
                "Inventory database connection pool exhausted",
                "Database connection allocation failure"
            ],
            "keep_alive": 0
        },
        timeout=120
    )

    response.raise_for_status()

    embeddings = response.json()["embeddings"]

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 768
    assert len(embeddings[1]) == 768

    print("Number of embeddings:", len(embeddings))
    print("Vector dimensions:", len(embeddings[0]))

    print("\nNomic embeddings: SUCCESS")


if __name__ == "__main__":
    test_qwen()
    test_embeddings()

    print("\nALL MODEL TESTS PASSED")
