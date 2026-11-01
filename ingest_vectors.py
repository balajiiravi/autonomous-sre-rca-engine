import re
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# Initialize Local In-Memory Engines (Zero Cloud Costs)
qdrant_client = QdrantClient(":memory:")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2") # Lightweight, 90MB footprint

def initialize_vector_db():
    qdrant_client.create_collection(
        collection_name="incident_runbooks",
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    
    # Pre-seed our Vector database with past real-world historical post-mortems/knowledge bases
    knowledge_base = [
        {
            "text": "Runbook: When inventory-db pool is exhausted, it is usually caused by leaked transactions or unindexed slow queries on the stock ledger table. Scale down application instances or kill idling backends.",
            "service": "inventory-db"
        },
        {
            "text": "Runbook: Payment service HTTP timeouts are downstream symptoms of a slow or locked transactional database layer. Verify state machine connections before restarting payments.",
            "service": "payment-service"
        }
    ]
    
    points = []
    for idx, doc in enumerate(knowledge_base):
        vector = embedding_model.encode(doc["text"]).tolist()
        points.append(PointStruct(
            id=idx,
            vector=vector,
            payload={"runbook_content": doc["text"], "target_service": doc["service"]}
        ))
        
    qdrant_client.upsert(collection_name="incident_runbooks", points=points)
    print("💾 Vector Database populated with structural historical resolution runbooks.")

if __name__ == "__main__":
    initialize_vector_db()
