"""Clause embeddings with JSON-text and native pgvector backends."""
import json
import math
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clause import Clause
from app.services.llm_client import get_llm_client


def _native_vectors() -> bool:
    return hasattr(Clause.embedding, "cosine_distance")


def _encode(vector):
    # SQLAlchemy's pgvector type accepts a list directly; Text needs JSON.
    return list(vector) if _native_vectors() else json.dumps(list(vector), allow_nan=False)


def _decode(value):
    try:
        vector = json.loads(value) if isinstance(value, str) else list(value)
        if not isinstance(vector, list) or not vector:
            return None
        vector = [float(x) for x in vector]
        return vector if all(math.isfinite(x) for x in vector) else None
    except (TypeError, ValueError):
        return None


def _cosine(a, b):
    a, b = _decode(a), _decode(b)
    if not a or not b or len(a) != len(b):
        return None
    norm = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / norm if norm else None


class VectorStore:
    """Store embeddings and search within an organization."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = get_llm_client()

    async def add_clause_embedding(self, clause_id: UUID, text: str, provider: Optional[str] = None) -> bool:
        try:
            embeddings = await self.llm_client.embed(texts=[text], provider=provider)
            if not embeddings or not embeddings[0]:
                return False
            clause = await self.db.get(Clause, clause_id)
            if clause is None:
                return False
            clause.embedding = _encode(embeddings[0])
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def _search(self, vector, organization_id, limit, threshold, exclude_id=None):
        if limit <= 0:
            return []
        filters = [Clause.organization_id == organization_id, Clause.embedding.is_not(None),
                   Clause.deleted_at.is_(None)]
        if exclude_id is not None:
            filters.append(Clause.id != exclude_id)
        if _native_vectors():
            distance = Clause.embedding.cosine_distance(vector)
            query = select(Clause, (1 - distance).label("similarity")).where(*filters).order_by(distance).limit(limit)
            rows = (await self.db.execute(query)).all()
            return [{"clause": c, "similarity": float(s)} for c, s in rows if s is not None and s >= threshold]
        clauses = (await self.db.execute(select(Clause).where(*filters))).scalars().all()
        matches = []
        for clause in clauses:
            similarity = _cosine(vector, clause.embedding)
            if similarity is not None and similarity >= threshold:
                matches.append({"clause": clause, "similarity": similarity})
        matches.sort(key=lambda result: result["similarity"], reverse=True)
        return matches[:limit]

    async def search_similar_clauses(self, query_text: str, organization_id: UUID, limit: int = 10,
                                     threshold: float = 0.7, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        embeddings = await self.llm_client.embed(texts=[query_text], provider=provider)
        if not embeddings or not embeddings[0]:
            return []
        return await self._search(embeddings[0], organization_id, limit, threshold)

    async def find_similar_clauses(self, clause_id: UUID, limit: int = 5,
                                   threshold: float = 0.8) -> List[Dict[str, Any]]:
        clause = await self.db.get(Clause, clause_id)
        if clause is None or clause.embedding is None:
            return []
        vector = _decode(clause.embedding)
        if vector is None:
            return []
        return await self._search(vector, clause.organization_id, limit, threshold, exclude_id=clause_id)

    async def batch_embed_clauses(self, organization_id: UUID, provider: Optional[str] = None,
                                  batch_size: int = 50) -> Dict[str, int]:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        query = select(Clause).where(Clause.organization_id == organization_id,
                                     Clause.embedding.is_(None), Clause.deleted_at.is_(None))
        clauses = (await self.db.execute(query)).scalars().all()
        processed = failed = 0
        for start in range(0, len(clauses), batch_size):
            batch = clauses[start:start + batch_size]
            embeddings = await self.llm_client.embed(texts=[c.content for c in batch], provider=provider)
            if not embeddings or len(embeddings) != len(batch):
                failed += len(batch)
                continue
            for clause, embedding in zip(batch, embeddings):
                try:
                    if not embedding:
                        failed += 1
                        continue
                    clause.embedding = _encode(embedding)
                    processed += 1
                except (TypeError, ValueError):
                    failed += 1
        await self.db.commit()
        return {"processed": processed, "failed": failed}


async def get_vector_store(db: AsyncSession) -> VectorStore:
    return VectorStore(db)
