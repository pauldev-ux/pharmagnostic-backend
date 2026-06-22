from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import ROLE_ADMIN, ROLE_DOCTOR, require_roles
from app.models.user import User
from app.schemas.audio import AudioOut
from app.services.audio_service import AudioService

router = APIRouter(tags=["audio-clinico"])

# Grabar, transcribir y eliminar: solo el médico. Consultar: administrador + médico.
can_read = require_roles(ROLE_ADMIN, ROLE_DOCTOR)
only_doctor = require_roles(ROLE_DOCTOR)


@router.post(
    "/prescriptions/{prescription_id}/audios",
    response_model=AudioOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_audio(
    prescription_id: int,
    file: UploadFile = File(...),
    duracion_segundos: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return AudioService(db).create_audio(prescription_id, file, duracion_segundos, current_user)


@router.get("/prescriptions/{prescription_id}/audios", response_model=list[AudioOut])
def list_audios(
    prescription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return AudioService(db).list_for_recipe(prescription_id)


@router.get("/audios/{audio_id}", response_model=AudioOut)
def get_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(can_read),
):
    return AudioService(db).get_audio(audio_id)


@router.post("/audios/{audio_id}/transcribe", response_model=AudioOut)
def transcribe_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    return AudioService(db).transcribe(audio_id, current_user)


@router.delete("/audios/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(only_doctor),
):
    AudioService(db).delete_audio(audio_id, current_user)
    return None
