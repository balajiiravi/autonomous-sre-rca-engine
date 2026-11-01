# Autonomous SRE Root Cause Analysis Engine

An AI-powered Site Reliability Engineering system that transforms raw production telemetry into dependency-aware incident trees and evidence-grounded root-cause hypotheses.

## Problem

Traditional log-based monitoring identifies individual errors but often fails to reconstruct how failures propagate across distributed service dependencies.

This project explores a Graph-Vector Hybrid RAG architecture that combines:

- **Graph retrieval:** Service dependency topology and failure propagation using Neo4j.
- **Vector retrieval:** Semantic search over telemetry and historical incidents using Qdrant.
- **LLM reasoning:** Evidence-grounded incident analysis using locally hosted Qwen models through Ollama.

## Architecture

Raw Telemetry → Parsing & Normalization → Incident Correlation → Graph + Vector Retrieval → Context Fusion → LLM-based RCA

## Current Implementation

- Production telemetry simulator with service dependency failures.
- Structured log parsing and event normalization.
- Request-ID-based incident correlation.
- Dependency-aware hierarchical incident reconstruction.
- Root-cause candidate selection with evidence preservation.

## Technology Stack

Python · FastAPI · Neo4j · Qdrant · Ollama · Qwen · Nomic Embeddings

## Project Status

Active development. Telemetry ingestion and initial incident correlation are implemented. Graph-backed topology retrieval, hybrid retrieval, and LLM-based reasoning are planned next.