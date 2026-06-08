from __future__ import annotations

from typing import Any

from ..clients.embedding_client import EmbeddingClient
from ..clients.llm_client import LlmClient
from ..core.flow_logger import log_flow
from ..models.message_model import MessageModel
from ..models.session_model import SessionModel
from ..repositories.learning_memory_repository import LearningMemoryRepository
from ..repositories.session_repository import SessionRepository
from .calibration_planner_service import CalibrationPlannerService
from .calibration_question_generation_error import (
    CalibrationQuestionGenerationError,
)
from .calibration_workflow_service import CalibrationWorkflowService
from .lab_primer_service import LabPrimerService
from .learning_plan_not_initialized_error import LearningPlanNotInitializedError
from .learning_workflow_service import LearningWorkflowService
from .session_manager_service import SessionManagerService
from .session_message_result import SessionMessageResult
from .session_not_found_error import SessionNotFoundError


class UserWorkflowService:
    """Coordinate the top-level learner session lifecycle across phase-specific services."""

    def __init__(
        self,
        *,
        session_manager_service: SessionManagerService,
        session_repository: SessionRepository,
        learning_memory_repository: LearningMemoryRepository,
        embedding_client: EmbeddingClient,
        llm_client: LlmClient,
        calibration_workflow_service: CalibrationWorkflowService,
        learning_workflow_service: LearningWorkflowService,
        lab_primer_service: LabPrimerService,
    ) -> None:
        self._session_manager_service = session_manager_service
        self._session_repository = session_repository
        self._learning_memory_repository = learning_memory_repository
        self._embedding_client = embedding_client
        self._llm_client = llm_client
        self._calibration_workflow_service = calibration_workflow_service
        self._learning_workflow_service = learning_workflow_service
        self._lab_primer_service = lab_primer_service

    async def start_new_session(
        self,
        *,
        goal: str,
        profile: dict[str, Any] | None,
    ) -> SessionModel:
        calibration_planner_service = CalibrationPlannerService(goal=goal, profile=profile)
        calibration_questions = await calibration_planner_service.questions(self._llm_client)

        session_model = self._session_manager_service.create_session(
            goal=goal,
            profile=profile,
            calibration_questions=calibration_questions,
        )

        question = self._session_manager_service.next_calibration_question(session_model)
        if question is None:
            raise CalibrationQuestionGenerationError(
                "No calibration questions were available for the new session."
            )

        assistant_message_model = MessageModel(
            role="assistant",
            content=question,
            metadata={"phase": session_model.phase, "stage": "calibration"},
        )
        session_model = self._session_manager_service.add_message(
            session_model,
            assistant_message_model,
        )

        profile_embedding = await self._embedding_client.embed(
            self._profile_text(goal, profile)
        )
        await self._learning_memory_repository.upsert_user_profile(
            session_id=session_model.id,
            goal=goal,
            experience_summary=self._profile_summary(profile),
            knowledge_vector=profile_embedding or None,
        )
        await self._learning_memory_repository.store_interaction(
            session_id=session_model.id,
            role="assistant",
            content=assistant_message_model.content,
            turn=session_model.current_turn(),
            metadata=assistant_message_model.metadata,
            phase=session_model.phase,
        )

        await self._session_repository.save(session_model)
        return session_model

    async def send_message(
        self,
        *,
        session_id: str,
        message: str,
        metadata: dict[str, Any] | None,
    ) -> SessionMessageResult:
        session_model = await self._restore_session(
            session_id=session_id,
            restored_event="api.sessions.message.restored",
            restored_description="RAG orchestrator restored the session from Elasticsearch before processing the message.",
        )

        user_message_model = MessageModel(role="user", content=message, metadata=metadata)
        session_model = self._session_manager_service.add_message(session_model, user_message_model)
        stripped_message = message.strip()

        if stripped_message.startswith("/lab"):
            return await self._handle_lab_command(
                session_model=session_model,
                message=message,
                metadata=metadata,
            )

        embedding = await self._embedding_client.embed(message)
        await self._learning_memory_repository.store_interaction(
            session_id=session_id,
            role="user",
            content=message,
            turn=session_model.current_turn(),
            embedding=embedding,
            metadata=metadata,
            phase=session_model.phase,
        )

        if session_model.phase in {"calibration", "tuning"}:
            assistant_message_model = await self._calibration_workflow_service.handle_answer(
                session_model=session_model,
                message=message,
                embedding=embedding,
            )
        elif session_model.phase == "learning":
            try:
                assistant_message_model = await self._learning_workflow_service.handle_answer(
                    session_model=session_model,
                    message=message,
                    embedding=embedding,
                )
            except ValueError as exc:
                raise LearningPlanNotInitializedError(str(exc)) from exc
        else:
            assistant_message_model = MessageModel(
                role="assistant",
                content="Learning program already completed. Use /no more to wrap up or ask for a recap.",
                metadata={"phase": session_model.phase, "stage": "complete"},
            )

        return await self._finalize_assistant_turn(
            session_model=session_model,
            assistant_message_model=assistant_message_model,
        )

    async def get_session(self, *, session_id: str) -> SessionModel:
        return await self._restore_session(
            session_id=session_id,
            restored_event="api.sessions.show.restored",
            restored_description="RAG orchestrator restored the session from Elasticsearch for resume.",
        )

    async def _restore_session(
        self,
        *,
        session_id: str,
        restored_event: str,
        restored_description: str,
    ) -> SessionModel:
        try:
            return self._session_manager_service.get_session(session_id)
        except KeyError:
            stored_session_model = await self._session_repository.get(session_id)
            if not stored_session_model:
                raise SessionNotFoundError(f"Session {session_id} not found")
            self._session_manager_service.load_session(stored_session_model)
            session_model = self._session_manager_service.get_session(session_id)
            log_flow(
                "rag-orchestrator",
                restored_event,
                restored_description,
                session_id=session_id,
                phase=session_model.phase,
            )
            return session_model

    async def _handle_lab_command(
        self,
        *,
        session_model: SessionModel,
        message: str,
        metadata: dict[str, Any] | None,
    ) -> SessionMessageResult:
        session_id = session_model.id
        requested_concept = self._resolve_lab_concept(session_model, message)
        lab_primer_document = self._lab_primer_service.generate(
            requested_concept,
            session_model.goal,
        )
        log_flow(
            "rag-orchestrator",
            "lab_primer.generated",
            "RAG orchestrator generated a lab primer package for the requested concept.",
            session_id=session_id,
            requested_concept=requested_concept,
            files=sorted(
                [name for name in lab_primer_document.keys() if name != "summary"]
            ),
        )

        await self._learning_memory_repository.store_interaction(
            session_id=session_id,
            role="user",
            content=message,
            turn=session_model.current_turn(),
            embedding=None,
            metadata={**(metadata or {}), "command": "lab"},
            phase=session_model.phase,
        )

        assistant_message_model = MessageModel(
            role="assistant",
            content=self._render_lab_response(lab_primer_document),
            metadata={
                "phase": session_model.phase,
                "stage": "lab_primer",
                "lab_concept": requested_concept,
            },
        )

        return await self._finalize_assistant_turn(
            session_model=session_model,
            assistant_message_model=assistant_message_model,
        )

    async def _finalize_assistant_turn(
        self,
        *,
        session_model: SessionModel,
        assistant_message_model: MessageModel,
    ) -> SessionMessageResult:
        session_model = self._session_manager_service.add_message(
            session_model,
            assistant_message_model,
        )
        await self._learning_memory_repository.store_interaction(
            session_id=session_model.id,
            role="assistant",
            content=assistant_message_model.content,
            turn=session_model.current_turn(),
            metadata=assistant_message_model.metadata,
            phase=session_model.phase,
        )
        await self._session_repository.save(session_model)
        return SessionMessageResult(
            session=session_model,
            last_message=assistant_message_model,
        )

    @staticmethod
    def _resolve_lab_concept(session_model: SessionModel, message: str) -> str:
        lab_arg = message.strip().split(maxsplit=1)
        requested_concept = lab_arg[1].strip() if len(lab_arg) == 2 else None
        if requested_concept:
            return requested_concept

        if session_model.phase == "learning" and session_model.tuning_plan:
            return session_model.tuning_plan[session_model.current_concept_index]["concept_name"]

        return session_model.goal

    @staticmethod
    def _render_lab_response(lab_primer_document: dict[str, str]) -> str:
        response_files = dict(lab_primer_document)
        summary = response_files.pop("summary")
        code_blocks = []
        for filename, content in response_files.items():
            if filename.endswith((".yml", ".yaml")):
                fence = "yaml"
            elif filename.lower() == "makefile":
                fence = "makefile"
            elif filename.endswith(".md"):
                fence = "markdown"
            else:
                fence = "text"
            code_blocks.append(
                "\n".join(
                    [
                        f"```{fence}",
                        f"# {filename}",
                        content,
                        "```",
                    ]
                )
            )
        return "\n\n".join([summary] + code_blocks)

    @staticmethod
    def _profile_summary(profile: dict[str, Any] | None) -> str:
        return str((profile or {}).get("summary") or "").strip()

    @classmethod
    def _profile_text(cls, goal: str, profile: dict[str, Any] | None) -> str:
        summary = cls._profile_summary(profile)
        if not summary:
            return goal
        return f"Goal: {goal}\nBackground: {summary}"
