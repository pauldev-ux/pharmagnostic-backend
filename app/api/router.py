from fastapi import APIRouter

from app.api.routes.alertas import router as alertas_router
from app.api.routes.audios import router as audios_router
from app.api.routes.auth import router as auth_router
from app.api.routes.clinical_history import router as clinical_history_router
from app.api.routes.diagnoses import router as diagnoses_router
from app.api.routes.health import router as health_router
from app.api.routes.medications import router as medications_router
from app.api.routes.pharmacological import router as pharmacological_router
from app.api.routes.patient_portal import router as patient_portal_router
from app.api.routes.pharmacy import router as pharmacy_router
from app.api.routes.patients import router as patients_router
from app.api.routes.prescriptions import router as prescriptions_router
from app.api.routes.profile import router as profile_router
from app.api.routes.roles import router as roles_router
from app.api.routes.users import router as users_router
from app.api.routes.validations import router as validations_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(roles_router)
api_router.include_router(users_router)
api_router.include_router(patients_router)
api_router.include_router(clinical_history_router)
api_router.include_router(diagnoses_router)
api_router.include_router(medications_router)
api_router.include_router(prescriptions_router)
api_router.include_router(audios_router)
api_router.include_router(alertas_router)
api_router.include_router(pharmacological_router)
api_router.include_router(validations_router)
api_router.include_router(pharmacy_router)
api_router.include_router(patient_portal_router)
