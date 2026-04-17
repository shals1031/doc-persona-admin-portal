import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.submission_repository import SubmissionRepository
from schemas.submission import QuestionAnswer, SubmissionWithAiProfile


class SubmissionService:
    def __init__(self, db: AsyncSession):
        self.repo = SubmissionRepository(db)

    async def get_submission(self, submission_id: uuid.UUID, tenant_id: uuid.UUID) -> SubmissionWithAiProfile:
        submission = await self.repo.get_by_id(submission_id, tenant_id)
        if submission is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        ai_profile = await self.repo.get_ai_profile(submission_id)

        # Fetch raw data and schema for Q&A table
        raw = await self.repo.get_raw_submission(submission_id)
        qa_data = []
        if raw and raw.submission_data and raw.form_version_id:
            schema = await self.repo.get_form_schema(raw.form_version_id)
            if schema and "questions" in schema:
                # Create a mapping of question ID to label
                q_map = {q["id"]: q.get("label", q["id"]) for q in schema["questions"]}
                
                # Sort questions based on schema order if possible
                # For now, let's just iterate over the submission_data
                for key, value in raw.submission_data.items():
                    if key in q_map:
                        confidence = raw.submission_data.get(f"{key}_confidence_level")
                        qa_data.append(QuestionAnswer(
                            question=q_map[key],
                            answer=str(value) if value is not None else None,
                            confidence=confidence
                        ))
                
                # Optionally sort qa_data based on schema order
                order = {q["id"]: i for i, q in enumerate(schema["questions"])}
                # Map question labels back to IDs to find their order, or just use the list of IDs from schema
                sorted_qa = []
                for q in schema["questions"]:
                    qid = q["id"]
                    if qid in raw.submission_data:
                        val = raw.submission_data[qid]
                        conf = raw.submission_data.get(f"{qid}_confidence_level")
                        sorted_qa.append(QuestionAnswer(
                            question=q.get("label", qid),
                            answer=str(val) if val is not None else None,
                            confidence=conf
                        ))
                qa_data = sorted_qa

        return SubmissionWithAiProfile(
            submission=submission, 
            ai_profile=ai_profile,
            qa_data=qa_data
        )
