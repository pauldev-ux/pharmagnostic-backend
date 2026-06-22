from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.documento_farmacologico import DocumentoFarmacologico
from app.models.fragmento_farmacologico import FragmentoFarmacologico


class PharmacologicalRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Documentos ---
    def get_document(self, document_id: int) -> Optional[DocumentoFarmacologico]:
        return (
            self.db.query(DocumentoFarmacologico)
            .filter(DocumentoFarmacologico.id_documento == document_id)
            .first()
        )

    def get_document_by_hash(self, file_hash: str) -> Optional[DocumentoFarmacologico]:
        return (
            self.db.query(DocumentoFarmacologico)
            .filter(DocumentoFarmacologico.hash_archivo == file_hash)
            .first()
        )

    def list_documents(self) -> list[DocumentoFarmacologico]:
        return (
            self.db.query(DocumentoFarmacologico)
            .order_by(DocumentoFarmacologico.id_documento.desc())
            .all()
        )

    def count_fragments(self, document_id: int) -> int:
        return (
            self.db.query(func.count(FragmentoFarmacologico.id_fragmento))
            .filter(FragmentoFarmacologico.id_documento == document_id)
            .scalar()
            or 0
        )

    def create_document(self, document: DocumentoFarmacologico) -> DocumentoFarmacologico:
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def save(self, document: DocumentoFarmacologico) -> DocumentoFarmacologico:
        self.db.commit()
        self.db.refresh(document)
        return document

    # --- Fragmentos ---
    def delete_fragments(self, document_id: int) -> int:
        deleted = (
            self.db.query(FragmentoFarmacologico)
            .filter(FragmentoFarmacologico.id_documento == document_id)
            .delete(synchronize_session=False)
        )
        return deleted

    def add_fragments(self, fragments: list[FragmentoFarmacologico]) -> None:
        self.db.add_all(fragments)

    def get_active_fragments(self) -> list[FragmentoFarmacologico]:
        """Fragmentos de documentos activos y ya procesados, con embedding."""
        return (
            self.db.query(FragmentoFarmacologico)
            .join(DocumentoFarmacologico)
            .filter(
                DocumentoFarmacologico.activo.is_(True),
                DocumentoFarmacologico.estado_procesamiento == "procesado",
                FragmentoFarmacologico.embedding.isnot(None),
            )
            .all()
        )
