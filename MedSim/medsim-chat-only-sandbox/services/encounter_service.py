from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from domain.models import INTERVIEW_MODE_FREE, PatientProfile, VALID_INTERVIEW_MODES
from services.patient_service import PatientService
from services.prompt_service import PromptService


class EncounterService:
    def __init__(self, patient_service: PatientService, prompt_service: PromptService):
        self.patient_service = patient_service
        self.prompt_service = prompt_service
        self.chat_histories: Dict[Tuple[str, str], List[dict]] = {}
        self.locked_model_by_history: Dict[Tuple[str, str], str] = {}
        self.encounters: Dict[str, Dict[str, Any]] = {}

    def get_session_id(self, request) -> str:
        header = request.headers.get("x-session-id") or request.headers.get("X-Session-Id")
        if header and header.strip():
            return header.strip()
        return str(hash(f"{request.client.host}|{request.headers.get('user-agent', '')}"))

    def normalize_mode(self, mode: Optional[str]) -> str:
        value = (mode or "").strip().lower()
        return value if value in VALID_INTERVIEW_MODES else INTERVIEW_MODE_FREE

    def start_encounter(self, patient_id: str, mode: str, request) -> Dict[str, Any]:
        profile = self.patient_service.get_patient(patient_id)
        if not profile:
            raise KeyError("Patient not found")
        session_id = self.get_session_id(request)
        encounter_id = uuid.uuid4().hex
        history_key = (session_id, encounter_id)
        self.chat_histories[history_key] = [{"role": "system", "content": self.prompt_service.build_patient_system_prompt(profile)}]
        self.encounters[encounter_id] = {
            "encounter_id": encounter_id,
            "session_id": session_id,
            "patient_id": patient_id,
            "mode": self.normalize_mode(mode),
            "started_at": time.time(),
            "finished_at": None,
            "doctor_submission": None,
        }
        return self.encounters[encounter_id]

    def get_encounter(self, encounter_id: str, request) -> Optional[Dict[str, Any]]:
        session_id = self.get_session_id(request)
        encounter = self.encounters.get(encounter_id)
        if not encounter or encounter.get("session_id") != session_id:
            return None
        return encounter

    def finish_encounter(self, encounter_id: str, payload: Dict[str, Any], request) -> Dict[str, Any]:
        encounter = self.get_encounter(encounter_id, request)
        if not encounter:
            raise KeyError("Encounter not found")
        profile = self.patient_service.get_patient(encounter["patient_id"])
        if not profile:
            raise KeyError("Patient not found")
        encounter["doctor_submission"] = payload
        encounter["finished_at"] = time.time()
        reveal = profile.true_case or PatientProfile.TrueCaseReveal(
            diagnostico_principal=profile.doctor_display_real_problem,
            diferenciales=[],
            indicaciones_plan=profile.unknown_real_problem,
            receta=None,
        )
        return {
            "encounter_id": encounter_id,
            "patient_id": encounter["patient_id"],
            "mode": encounter.get("mode", INTERVIEW_MODE_FREE),
            "doctor_submission": payload,
            "true_diagnosis": profile.doctor_display_real_problem,
            "true_details": profile.unknown_real_problem,
            "true_case": reveal.model_dump(),
            "finished_at": encounter["finished_at"],
        }

    def get_history(self, history_key: Tuple[str, str]) -> List[dict]:
        return self.chat_histories.setdefault(history_key, [])

    def ensure_history(self, history_key: Tuple[str, str], profile: PatientProfile) -> List[dict]:
        if history_key not in self.chat_histories:
            self.chat_histories[history_key] = [{"role": "system", "content": self.prompt_service.build_patient_system_prompt(profile)}]
            self.locked_model_by_history.pop(history_key, None)
        return self.chat_histories[history_key]

    def append_user_message(self, history_key: Tuple[str, str], message: str) -> None:
        self.chat_histories[history_key].append({"role": "user", "content": message})

    def append_assistant_message(self, history_key: Tuple[str, str], message: str) -> None:
        self.chat_histories[history_key].append({"role": "assistant", "content": message})
        if len(self.chat_histories[history_key]) > 24:
            system_msg = self.chat_histories[history_key][0]
            self.chat_histories[history_key] = [system_msg] + self.chat_histories[history_key][-23:]
