from typing import Optional

from sqlalchemy.orm import Session

from app.models.audio_clinico import AudioClinico


class AudioRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, audio_id: int) -> Optional[AudioClinico]:
        return self.db.query(AudioClinico).filter(AudioClinico.id_audio == audio_id).first()

    def get_by_recipe(self, recipe_id: int) -> list[AudioClinico]:
        return (
            self.db.query(AudioClinico)
            .filter(AudioClinico.id_receta == recipe_id)
            .order_by(AudioClinico.id_audio.desc())
            .all()
        )

    def create(self, audio: AudioClinico) -> AudioClinico:
        self.db.add(audio)
        self.db.commit()
        self.db.refresh(audio)
        return audio

    def save(self, audio: AudioClinico) -> AudioClinico:
        self.db.commit()
        self.db.refresh(audio)
        return audio

    def delete(self, audio: AudioClinico) -> None:
        self.db.delete(audio)
        self.db.commit()
