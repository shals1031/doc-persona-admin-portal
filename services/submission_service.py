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
                
                # Section mapping provided in the requirement
                sections_config = [
                    {
                        "id": "section_1",
                        "title": "SECTION 1: MR IDENTIFICATION",
                        "description": "Please provide your details and the date of this profiling interaction.",
                        "order": 1,
                        "questions": ["q1_1", "q1_2", "q1_3"]
                    },
                    {
                        "id": "section_2",
                        "title": "SECTION 2: DOCTOR IDENTIFICATION",
                        "description": "Enter the doctor's basic information. Use the name as it appears on their clinic board.",
                        "order": 2,
                        "questions": ["q2_1", "q1_4", "q2_2", "q2_10", "q2_3", "q2_4", "q2_5", "q2_8", "q2_9", "q2_6", "q2_7"]
                    },
                    {
                        "id": "section_3",
                        "title": "SECTION 3: PRACTICE PROFILE & BUSINESS POTENTIAL",
                        "description": "Assess the doctor's practice size and business potential. Base your answers on what you have observed during visits.",
                        "order": 3,
                        "questions": ["q3_1", "q3_4", "q3_5", "q3_6"]
                    },
                    {
                        "id": "section_4",
                        "title": "SECTION 4: GENERAL PRESCRIBING BEHAVIOR",
                        "description": "Understand how the doctor prescribes medicines in general.",
                        "order": 4,
                        "questions": ["q4_3", "q4_4", "q4_5"]
                    },
                    {
                        "id": "section_5",
                        "title": "SECTION 5: TREATMENT APPROACH",
                        "description": "Understand how this doctor thinks about treatment decisions.",
                        "order": 5,
                        "questions": ["q5_1", "q5_2"]
                    },
                    {
                        "id": "section_6",
                        "title": "SECTION 6: ENGAGEMENT PREFERENCES",
                        "description": "Understand how this doctor prefers to receive information and interact with pharma companies.",
                        "order": 6,
                        "questions": ["q6_1", "q6_2", "q6_3", "q6_4", "q6_5", "q6_6", "q6_7"]
                    },
                    {
                        "id": "section_7",
                        "title": "SECTION 7: RELATIONSHIP & COMPETITIVE INFORMATION",
                        "description": "Overall perception and competitive landscape.",
                        "order": 7,
                        "questions": ["q7_1", "q7_2", "q7_2_other", "q7_3", "q7_3_other"]
                    },
                    {
                        "id": "section_8",
                        "title": "SECTION 8: YOUR OVERALL ASSESSMENT",
                        "description": "Based on your interaction, provide your overall assessment of this doctor.",
                        "order": 8,
                        "questions": ["q8_1", "q8_2", "q8_4"]
                    },
                    {
                        "id": "section_9",
                        "title": "SECTION 9: NVM-LC BRAND MODULE",
                        "description": "About NVM-LC: Folic Acid + Levo-carnitine + Methylcobalamin + Vitamin E",
                        "order": 9,
                        "questions": ["q9_1", "q9_2", "q9_4", "q9_4_other", "q9_5", "q9_7", "q9_8", "q9_9", "q9_10"]
                    },
                    {
                        "id": "section_10",
                        "title": "SECTION 10: COMIG BRAND MODULE",
                        "description": "About Comig: Naproxen Sodium 250/500mg + Domperidone 10mg for migraine treatment",
                        "order": 10,
                        "questions": ["q10_1", "q10_1_other", "q10_2", "q10_3", "q10_4", "q10_5", "q10_5_other", "q10_7", "q10_9", "q10_10", "q10_11", "q10_12"]
                    }
                ]

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
