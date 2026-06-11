import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.submission_repository import SubmissionRepository
from schemas.submission import QuestionAnswer, SectionQuestions, SubmissionWithAiProfile


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
        sections_data = []

        if raw and raw.submission_data and raw.form_version_id:
            schema = await self.repo.get_form_schema(raw.form_version_id)
            if schema and "questions" in schema:
                # Create a mapping of question ID to label/data
                q_map = {q["id"]: q for q in schema["questions"]}
                
                # Dynamically load the sections from the submitted form's schema
                sections_config = sorted(schema.get("sections", []), key=lambda x: x.get("order", 0))

                # Process by section
                for sec in sections_config:
                    section_qs = []
                    for qid in sec["questions"]:
                        is_answered = qid in raw.submission_data
                        label = q_map[qid].get("label", qid) if qid in q_map else qid
                        
                        display_answer = None
                        conf = None
                        
                        if is_answered:
                            val = raw.submission_data[qid]
                            conf = raw.submission_data.get(f"{qid}_confidence_level")
                            
                            # Map value to label if options are available
                            display_answer = val
                            if qid in q_map and "options" in q_map[qid] and val is not None:
                                options = q_map[qid]["options"]
                                if isinstance(val, list):
                                    labels = []
                                    for v in val:
                                        opt_label = next((opt["label"] for opt in options if opt["value"] == v), str(v))
                                        labels.append(opt_label)
                                    display_answer = ", ".join(labels)
                                else:
                                    display_answer = next((opt["label"] for opt in options if opt["value"] == val), val)
                        
                        qa_item = QuestionAnswer(
                            question=label,
                            answer=str(display_answer) if display_answer is not None else None,
                            confidence=conf,
                            is_answered=is_answered
                        )
                        section_qs.append(qa_item)
                        qa_data.append(qa_item)
                    
                    if section_qs:
                        sections_data.append(SectionQuestions(
                            title=sec["title"],
                            description=sec.get("description"),
                            questions=section_qs
                        ))

        return SubmissionWithAiProfile(
            submission=submission, 
            ai_profile=ai_profile,
            qa_data=qa_data,
            sections=sections_data
        )
