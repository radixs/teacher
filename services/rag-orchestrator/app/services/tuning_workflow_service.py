from __future__ import annotations

from ..clients.llm_client import LlmClient
from ..core.flow_logger import log_flow
from ..models.message_model import MessageModel
from ..models.session_model import SessionModel
from ..repositories.learning_memory_repository import LearningMemoryRepository
from .learning_coordinator_service import LearningCoordinatorService
from .resource_discovery_service import ResourceDiscoveryService
from .session_manager_service import SessionManagerService
from .tuning_program_generator_service import TuningProgramGeneratorService


class TuningWorkflowService:
    """Own the transition from completed calibration into active learning."""

    def __init__(
        self,
        *,
        session_manager_service: SessionManagerService,
        learning_memory_repository: LearningMemoryRepository,
        resource_discovery_service: ResourceDiscoveryService,
        llm_client: LlmClient,
    ) -> None:
        self._session_manager_service = session_manager_service
        self._learning_memory_repository = learning_memory_repository
        self._resource_discovery_service = resource_discovery_service
        self._llm_client = llm_client

    async def complete_calibration(self, session_model: SessionModel) -> MessageModel:
        session_id = session_model.id
        tuning_program_generator_service = TuningProgramGeneratorService(
            goal=session_model.goal,
            calibration_history=session_model.calibration_history,
            external_resources=[],
        )
        search_query = tuning_program_generator_service.build_search_query()
        external_resources = await self._resource_discovery_service.discover_resources(
            session_id=session_id,
            query=search_query,
            enrich=False,
            extra_tags=[session_model.goal, "search", "calibration"],
        )

        tuning_program_generator_service = TuningProgramGeneratorService(
            goal=session_model.goal,
            calibration_history=session_model.calibration_history,
            external_resources=external_resources,
        )
        plan = await tuning_program_generator_service.generate(self._llm_client)
        session_model = self._session_manager_service.set_tuning_plan(session_model, plan)
        session_model = self._session_manager_service.begin_learning(session_model)

        for plan_node in plan:
            await self._learning_memory_repository.store_dependency_node(
                node={**plan_node, "session_id": session_id},
            )
            await self._resource_discovery_service.persist_resources(
                session_id=session_id,
                resources=plan_node.get("resources", []),
                concept_id=plan_node.get("concept_id"),
                extra_tags=[
                    session_model.goal,
                    plan_node.get("concept_id", ""),
                    plan_node.get("concept_name", ""),
                    "roadmap",
                ],
            )

        summary_lines = [
            f"- {calibration_record['question']} -> {calibration_record.get('answer', 'pending')}"
            for calibration_record in session_model.calibration_history
        ]
        learning_coordinator_service = LearningCoordinatorService(
            plan=session_model.tuning_plan,
            index=session_model.current_concept_index,
        )
        lesson_overview = learning_coordinator_service.build_overview()
        summary = (
            "Calibration complete. Generated tuning roadmap with "
            f"{len(plan)} concepts. Here's what we've captured so far:\n"
            + "\n".join(summary_lines)
        )
        message_body = (
            summary
            + "\n\n"
            + "**Next step: Phase 2 - Learning**\n"
            + lesson_overview
        )
        assistant_message_model = MessageModel(
            role="assistant",
            content=message_body,
            metadata={
                "phase": session_model.phase,
                "stage": "learning_intro",
                "concept_id": learning_coordinator_service.current_node().get("concept_id"),
            },
        )
        log_flow(
            "rag-orchestrator",
            "learning.plan_ready",
            "RAG orchestrator finished calibration, generated the roadmap, and entered the learning phase.",
            session_id=session_id,
            concepts=len(plan),
            first_concept=learning_coordinator_service.current_node().get("concept_id"),
            search_query=search_query,
            external_resources=len(external_resources),
        )
        return assistant_message_model
