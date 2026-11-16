import pytest
from backend.app.services.document_service import document_service
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.cache_service import cache_service
from backend.app.services.session_service import session_service

def test_document_deletion_tombstone(db):
    doc = document_service.ingest_document(
        db=db,
        title="Compensation Memo",
        department="HR",
        raw_text="Ravi's monthly salary is INR 90,000. CANARY: CANARY-HR-78923-SAL",
        permitted_principals=["hr_manager", "finance_director"]
    )
    assert doc.is_tombstoned is False

    # Perform deletion
    deleted_doc = document_service.delete_document(db, doc.id)
    assert deleted_doc.is_tombstoned is True
    assert deleted_doc.indexing_status == "deleted"

    # Verify retrieval blocks tombstoned document
    chunks, trace = retrieval_service.retrieve_permitted_chunks(
        db=db,
        query="What is Ravi's salary?",
        principal_id="hr_manager",
        force_fault_stale_index=False
    )
    assert len(chunks) == 0
    assert trace["permitted_count"] == 0

def test_permission_revocation_semantics(db):
    doc = document_service.ingest_document(
        db=db,
        title="Quarterly Budget",
        department="Finance",
        raw_text="Project Phoenix acquisition reserve is USD 42.5 million.",
        permitted_principals=["cfo", "head_of_ma"]
    )

    # Both principals have initial access
    cfo_chunks, _ = retrieval_service.retrieve_permitted_chunks(
        db=db, query="Project Phoenix reserve", principal_id="cfo"
    )
    assert len(cfo_chunks) > 0

    ma_chunks, _ = retrieval_service.retrieve_permitted_chunks(
        db=db, query="Project Phoenix reserve", principal_id="head_of_ma"
    )
    assert len(ma_chunks) > 0

    # Revoke head_of_ma
    document_service.update_acls(db, doc.id, new_permitted_principals=["cfo"])

    # Revoked principal is blocked
    revoked_chunks, _ = retrieval_service.retrieve_permitted_chunks(
        db=db, query="Project Phoenix reserve", principal_id="head_of_ma"
    )
    assert len(revoked_chunks) == 0

    # Authorized principal still has access!
    still_auth_chunks, _ = retrieval_service.retrieve_permitted_chunks(
        db=db, query="Project Phoenix reserve", principal_id="cfo"
    )
    assert len(still_auth_chunks) > 0

def test_cache_invalidation_on_deletion(db):
    doc = document_service.ingest_document(
        db=db,
        title="Tax Assessment",
        department="Finance",
        raw_text="Contingency tax reserve of EUR 3,850,000 established in Ireland.",
        permitted_principals=["tax_director"]
    )

    # Store cache
    cache_service.store_cached_answer(
        db=db,
        query="tax reserve amount",
        scope="test_cache",
        principal_id="tax_director",
        answer_mode="local_extractive",
        answer_text="EUR 3,850,000",
        citations=[],
        source_docs=[doc]
    )

    # Read from cache before deletion (hit)
    hit, trace = cache_service.get_cached_answer(
        db=db, query="tax reserve amount", scope="test_cache",
        principal_id="tax_director", answer_mode="local_extractive"
    )
    assert hit is not None
    assert trace["cache_hit"] is True

    # Delete document
    document_service.delete_document(db, doc.id)

    # Read from cache after deletion (must be invalidated and return None)
    miss, trace_after = cache_service.get_cached_answer(
        db=db, query="tax reserve amount", scope="test_cache",
        principal_id="tax_director", answer_mode="local_extractive"
    )
    assert miss is None
    assert trace_after["cache_hit"] is False
