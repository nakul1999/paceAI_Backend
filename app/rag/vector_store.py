import io

from app.services.openai_service import client
from app.rag.documents import RAG_DOCUMENTS

VECTOR_STORE_NAME = "PaceAI Knowledge Base"


def get_or_create_vector_store() -> str:
    existing_stores = client.vector_stores.list().data

    for store in existing_stores:
        if store.name == VECTOR_STORE_NAME:
            return store.id

    vector_store = client.vector_stores.create(
        name=VECTOR_STORE_NAME
    )

    file_ids = []

    for filename, content in RAG_DOCUMENTS.items():
        file_obj = io.BytesIO(content.encode("utf-8"))
        file_obj.name = filename

        uploaded_file = client.files.create(
            file=(filename, file_obj, "text/plain"),
            purpose="assistants",
        )

        file_ids.append(uploaded_file.id)

    client.vector_stores.file_batches.create_and_poll(
        vector_store_id=vector_store.id,
        file_ids=file_ids,
    )

    return vector_store.id