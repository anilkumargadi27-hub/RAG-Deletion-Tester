import os
import re
from typing import List, Dict, Any, Optional
import numpy as np
import chromadb
from chromadb.config import Settings as ChromaSettings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.config import settings

class EmbeddingService:
    def __init__(self):
        self._embedder = None
        self._mode = "fastembed"
        self._init_error = None
        self._setup()

    def _setup(self):
        try:
            # Use fastembed with local cache
            from fastembed import TextEmbedding
            os.environ["FASTEMBED_CACHE_PATH"] = str(settings.model_cache_dir)
            self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            self._mode = "semantic_vector"
        except Exception as e:
            self._init_error = str(e)
            self._mode = "tfidf_lexical"

    @property
    def mode(self) -> str:
        return self._mode

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self._embedder is not None:
            try:
                embeddings = list(self._embedder.embed(texts))
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                self._init_error = str(e)
                self._mode = "tfidf_lexical"
        # Fallback dummy embedding if TFIDF mode is active
        return [[0.0] * 384 for _ in texts]

class VectorStoreService:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.chroma_dir),
            settings=ChromaSettings(anonymized_telemetry=False, is_persistent=True)
        )
        self.embedding_service = EmbeddingService()
        self._tfidf_indexes: Dict[str, Dict[str, Any]] = {} # collection_name -> {vectorizer, doc_ids, contents, metadatas}

    def get_or_create_collection(self, name: str = "production_documents"):
        # Chroma collection names must be 3-63 chars, alphanumeric, hyphens, underscores
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:63]
        if len(clean_name) < 3:
            clean_name = f"col_{clean_name}"
        return self.chroma_client.get_or_create_collection(
            name=clean_name,
            metadata={"description": "ForgetCheck document chunks"}
        )

    def add_chunks(self, collection_name: str, chunks: List[Dict[str, Any]]):
        """Add chunks to Chroma and also maintain TF-IDF index for fallback."""
        if not chunks:
            return

        ids = [c["chunk_id"] for c in chunks]
        texts = [c["content"] for c in chunks]
        metadatas = [c.get("metadata", {}) for c in chunks]

        # 1. Add to Chroma
        collection = self.get_or_create_collection(collection_name)
        embeddings = self.embedding_service.embed_texts(texts)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        # 2. Update TF-IDF memory index
        if collection_name not in self._tfidf_indexes:
            self._tfidf_indexes[collection_name] = {"ids": [], "texts": [], "metadatas": []}

        # Deduplicate and append
        existing_ids = set(self._tfidf_indexes[collection_name]["ids"])
        for c in chunks:
            cid = c["chunk_id"]
            if cid in existing_ids:
                idx = self._tfidf_indexes[collection_name]["ids"].index(cid)
                self._tfidf_indexes[collection_name]["texts"][idx] = c["content"]
                self._tfidf_indexes[collection_name]["metadatas"][idx] = c.get("metadata", {})
            else:
                self._tfidf_indexes[collection_name]["ids"].append(cid)
                self._tfidf_indexes[collection_name]["texts"].append(c["content"])
                self._tfidf_indexes[collection_name]["metadatas"].append(c.get("metadata", {}))

    def delete_document_chunks(self, collection_name: str, document_id: str):
        """Delete all chunks for a document from vector store."""
        collection = self.get_or_create_collection(collection_name)
        try:
            collection.delete(where={"document_id": document_id})
        except Exception:
            pass

        # Also purge from TF-IDF index
        if collection_name in self._tfidf_indexes:
            data = self._tfidf_indexes[collection_name]
            kept_indices = [
                i for i, meta in enumerate(data["metadatas"])
                if meta.get("document_id") != document_id
            ]
            self._tfidf_indexes[collection_name] = {
                "ids": [data["ids"][i] for i in kept_indices],
                "texts": [data["texts"][i] for i in kept_indices],
                "metadatas": [data["metadatas"][i] for i in kept_indices]
            }

    def delete_collection(self, collection_name: str):
        try:
            clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', collection_name)[:63]
            self.chroma_client.delete_collection(name=clean_name)
        except Exception:
            pass
        if collection_name in self._tfidf_indexes:
            del self._tfidf_indexes[collection_name]

    def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 4,
        where_filter: Optional[Dict[str, Any]] = None,
        force_tfidf: bool = False
    ) -> List[Dict[str, Any]]:
        use_tfidf = force_tfidf or (self.embedding_service.mode == "tfidf_lexical")

        if not use_tfidf:
            try:
                collection = self.get_or_create_collection(collection_name)
                query_emb = self.embedding_service.embed_texts([query])
                results = collection.query(
                    query_embeddings=query_emb,
                    n_results=min(top_k, max(1, collection.count())),
                    where=where_filter if where_filter else None
                )
                output = []
                if results and results.get("ids") and results["ids"][0]:
                    for i in range(len(results["ids"][0])):
                        output.append({
                            "chunk_id": results["ids"][0][i],
                            "content": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                            "score": float(results["distances"][0][i]) if results.get("distances") else 0.0,
                            "retrieval_mode": "semantic_vector"
                        })
                return output
            except Exception:
                # If Chroma query fails, fall back to TF-IDF
                pass

        # TF-IDF Lexical Search Fallback
        return self._search_tfidf(collection_name, query, top_k, where_filter)

    def _search_tfidf(
        self,
        collection_name: str,
        query: str,
        top_k: int = 4,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        data = self._tfidf_indexes.get(collection_name)
        if not data or not data["texts"]:
            return []

        # Apply where_filter if provided
        indices = list(range(len(data["texts"])))
        if where_filter:
            filtered_indices = []
            for i in indices:
                meta = data["metadatas"][i]
                match = True
                for k, v in where_filter.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if match:
                    filtered_indices.append(i)
            indices = filtered_indices

        if not indices:
            return []

        filtered_texts = [data["texts"][i] for i in indices]
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform(filtered_texts)
            query_vec = vectorizer.transform([query])
            sims = cosine_similarity(query_vec, tfidf_matrix).flatten()

            # Rank by similarity score
            top_indices = np.argsort(sims)[::-1][:top_k]
            results = []
            for rank_idx in top_indices:
                orig_idx = indices[rank_idx]
                score = float(sims[rank_idx])
                if score > 0.01: # Relevant threshold
                    results.append({
                        "chunk_id": data["ids"][orig_idx],
                        "content": data["texts"][orig_idx],
                        "metadata": data["metadatas"][orig_idx],
                        "score": score,
                        "retrieval_mode": "tfidf_lexical"
                    })
            return results
        except Exception:
            return []

vector_store_service = VectorStoreService()
