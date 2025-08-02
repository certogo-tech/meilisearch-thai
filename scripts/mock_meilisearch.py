#!/usr/bin/env python3
"""
Mock Meilisearch server for testing Thai Tokenizer deployment
"""

import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import uvicorn

app = FastAPI(title="Mock Meilisearch Server", version="1.15.2")

# Mock data storage
mock_indexes = {}
mock_documents = {}
mock_stats = {
    "health": "available",
    "status": "available",
    "version": "1.15.2",
    "commit_sha": "mock-commit",
    "commit_date": "2024-01-01T00:00:00Z",
    "pkg_version": "1.15.2"
}

def verify_api_key(authorization: Optional[str] = Header(None)):
    """Verify API key for protected endpoints"""
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization.replace("Bearer ", "")
        if api_key in ["test-key", "your-secure-api-key", "development-key"]:
            return api_key
    return None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "available"
    })

@app.get("/version")
async def version_info():
    """Version information endpoint"""
    return JSONResponse(mock_stats)

@app.get("/stats")
async def get_stats(authorization: Optional[str] = Header(None)):
    """Get Meilisearch statistics"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return JSONResponse({
        "database_size": 1024000,
        "last_update": datetime.now().isoformat(),
        "indexes": {
            "documents": {
                "number_of_documents": len(mock_documents.get("documents", {})),
                "is_indexing": False,
                "field_distribution": {
                    "content": 100,
                    "title": 50
                }
            }
        }
    })

@app.get("/indexes")
async def list_indexes(authorization: Optional[str] = Header(None)):
    """List all indexes"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return JSONResponse({
        "results": [
            {
                "uid": "documents",
                "primaryKey": "id",
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": datetime.now().isoformat()
            }
        ],
        "offset": 0,
        "limit": 20,
        "total": 1
    })

@app.post("/indexes")
async def create_index(
    index_data: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    """Create a new index"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    uid = index_data.get("uid")
    if not uid:
        raise HTTPException(status_code=400, detail="Index uid is required")
    
    mock_indexes[uid] = {
        "uid": uid,
        "primaryKey": index_data.get("primaryKey"),
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat()
    }
    
    return JSONResponse(mock_indexes[uid], status_code=202)

@app.get("/indexes/{index_uid}")
async def get_index(
    index_uid: str,
    authorization: Optional[str] = Header(None)
):
    """Get index information"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if index_uid not in mock_indexes:
        # Create default documents index if it doesn't exist
        if index_uid == "documents":
            mock_indexes[index_uid] = {
                "uid": index_uid,
                "primaryKey": "id",
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Index not found")
    
    return JSONResponse(mock_indexes[index_uid])

@app.get("/indexes/{index_uid}/settings")
async def get_index_settings(
    index_uid: str,
    authorization: Optional[str] = Header(None)
):
    """Get index settings"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return JSONResponse({
        "searchableAttributes": ["*"],
        "filterableAttributes": [],
        "sortableAttributes": [],
        "rankingRules": [
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness"
        ],
        "stopWords": [],
        "synonyms": {},
        "distinctAttribute": None,
        "typoTolerance": {
            "enabled": True,
            "minWordSizeForTypos": {
                "oneTypo": 5,
                "twoTypos": 9
            },
            "disableOnWords": [],
            "disableOnAttributes": []
        }
    })

@app.post("/indexes/{index_uid}/documents")
async def add_documents(
    index_uid: str,
    documents: list,
    authorization: Optional[str] = Header(None)
):
    """Add documents to index"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if index_uid not in mock_documents:
        mock_documents[index_uid] = {}
    
    task_uid = len(mock_documents[index_uid]) + 1
    
    for doc in documents:
        doc_id = doc.get("id", f"doc_{len(mock_documents[index_uid])}")
        mock_documents[index_uid][doc_id] = doc
    
    return JSONResponse({
        "taskUid": task_uid,
        "indexUid": index_uid,
        "status": "enqueued",
        "type": "documentAdditionOrUpdate",
        "enqueuedAt": datetime.now().isoformat()
    }, status_code=202)

@app.post("/indexes/{index_uid}/search")
async def search_documents(
    index_uid: str,
    search_data: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    """Search documents in index"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    query = search_data.get("q", "")
    limit = search_data.get("limit", 20)
    
    # Simple mock search - return all documents if no query, or filter by content
    results = []
    if index_uid in mock_documents:
        for doc_id, doc in mock_documents[index_uid].items():
            if not query or query.lower() in str(doc.get("content", "")).lower():
                results.append(doc)
                if len(results) >= limit:
                    break
    
    return JSONResponse({
        "hits": results,
        "query": query,
        "processingTimeMs": 5,
        "limit": limit,
        "offset": 0,
        "estimatedTotalHits": len(results)
    })

@app.get("/tasks/{task_uid}")
async def get_task(
    task_uid: int,
    authorization: Optional[str] = Header(None)
):
    """Get task status"""
    api_key = verify_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return JSONResponse({
        "uid": task_uid,
        "indexUid": "documents",
        "status": "succeeded",
        "type": "documentAdditionOrUpdate",
        "details": {
            "receivedDocuments": 1,
            "indexedDocuments": 1
        },
        "duration": "PT0.001S",
        "enqueuedAt": "2024-01-01T00:00:00Z",
        "startedAt": "2024-01-01T00:00:00Z",
        "finishedAt": "2024-01-01T00:00:01Z"
    })

if __name__ == "__main__":
    print("🚀 Starting Mock Meilisearch Server...")
    print("📍 Server will be available at: http://localhost:7700")
    print("🔑 Accepted API keys: test-key, your-secure-api-key, development-key")
    print("📋 Available endpoints:")
    print("   - GET  /health")
    print("   - GET  /version")
    print("   - GET  /stats")
    print("   - GET  /indexes")
    print("   - POST /indexes")
    print("   - GET  /indexes/{uid}")
    print("   - GET  /indexes/{uid}/settings")
    print("   - POST /indexes/{uid}/documents")
    print("   - POST /indexes/{uid}/search")
    print("   - GET  /tasks/{uid}")
    
    uvicorn.run(app, host="0.0.0.0", port=7700, log_level="info")