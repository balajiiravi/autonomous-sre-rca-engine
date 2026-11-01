import os
import re
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

# --- CONFIGURATION CREDENTIALS ---
NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "localpassword123"

# Initialize Local Vector and Embedding Models
qdrant_client = QdrantClient(":memory:")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

LOG_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<service>[^\]]+)\]\s+\[(?P<level>[^\]]+)\]\s+(?P<message>.*)$"
)

def get_network_dependencies() -> dict:
    """Queries Neo4j to build an in-memory map of system call paths."""
    dependency_map = {}
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    query = """
    MATCH (a:Microservice)-[:DEPENDS_ON]->(b:Microservice)
    RETURN a.name as service, b.name as dependency
    """
    with driver.session() as session:
        result = session.run(query)
        for record in result:
            dependency_map[record["service"]] = record["dependency"]
            
    driver.close()
    return dependency_map

def build_hierarchical_incident_tree(log_filepath="production_telemetry.log"):
    if not os.path.exists(log_filepath):
        print("❌ Error: Log file not found.")
        return

    # Fetch physical architecture rules directly from Neo4j Aura Cloud
    infra_blueprint = get_network_dependencies()
    
    with open(log_filepath, "r") as f:
        lines = f.readlines()

    parsed_errors = {}
    for line in lines:
        match = LOG_PATTERN.match(line.strip())
        if match:
            data = match.groupdict()
            if data["level"] in ["ERROR", "CRITICAL"]:
                parsed_errors[data["service"]] = f"[{data['level']}] {data['message']}"

    # --- AGENTIC HIERARCHICAL SYNTHESIS ---
    # We enforce infrastructure topology context onto flat, linear logs
    hierarchical_markdown = "# Incident Triage Document - Structural Trace\n"
    
    # Trace Hop 0: Edge Layer
    if "frontend-service" in parsed_errors:
        hierarchical_markdown += f"## [HOP 0 - EDGE DISPATCH] frontend-service\n"
        hierarchical_markdown += f"   └── Local Symptom Observed: {parsed_errors['frontend-service']}\n"
        
        # Trace Hop 1: Downstream Internal Application Mesh
        next_hop = infra_blueprint.get("frontend-service")
        if next_hop and next_hop in parsed_errors:
            hierarchical_markdown += f"   └── [HOP 1 - INTERNAL APP MESH] {next_hop}\n"
            hierarchical_markdown += f"       └── Downstream State: {parsed_errors[next_hop]}\n"
            
            # Trace Hop 2: Deep Core Infrastructure Layer
            core_hop = infra_blueprint.get(next_hop)
            if core_hop and core_hop in parsed_errors:
                hierarchical_markdown += f"       └── [HOP 2 - STORAGE ENGINE ROOT] {core_hop}\n"
                hierarchical_markdown += f"           └── Hardware/Resource Exception: {parsed_errors[core_hop]}\n"

    print("\n🌲 Flat Logs Rebuilt into a Graph-Grounded Hierarchical Context Matrix:")
    print("=" * 80)
    print(hierarchical_markdown)
    print("=" * 80)

    # Ingest this rich, non-linear document into Qdrant
    qdrant_client.create_collection("structured_incidents", VectorParams(size=384, distance=Distance.COSINE))
    vector = embedding_model.encode(hierarchical_markdown).tolist()
    qdrant_client.upsert(
        collection_name="structured_incidents",
        points=[PointStruct(id=1, vector=vector, payload={"structured_report": hierarchical_markdown})]
    )
    print("💾 Complex nested payload written into local Qdrant collection vectors.")

if __name__ == "__main__":
    build_hierarchical_incident_tree()
