#%%
import json 
from pathlib import Path 
from embedding import SimpleVectorStore

#%%
class StudentFeedbackEngine:

    def __init__(self, vector_store: SimpleVectorStore):
        self.store = vector_store

    def build_feedback_prompt(
        self, draft_text: str, module_code: str = "CMP020C106S"
    ) -> tuple[str, list[dict]]:
        """Retrieves module brief & rubric to evaluate a student's draft work."""
        # 1. Retrieve marking criteria, deliverables, and rubric for this draft
        query = f"{module_code} rubric marking criteria deliverables requirements learning outcomes"
        retrieved_chunks = self.store.retrieve(query, top_k=4)

        # 2. Format retrieved context
        context_str = "\n\n".join(
            [
                f"--- Context Chunk [{i+1}] ({c['source_file']} - {c['section']}) ---\n{c['content']}"
                for i, c in enumerate(retrieved_chunks)
            ]
        )

        # 3. Construct evaluation prompt
        prompt = f"""You are an Academic Tutor assisting a student with formative feedback.
Evaluate the student's draft submission against the official Assessment Brief & Rubric provided below.

### OFFICIAL ASSESSMENT BRIEF & RUBRIC CONTEXT:
{context_str}

### STUDENT DRAFT SUBMISSION:
{draft_text}

### INSTRUCTIONS:
1. **Brief Alignment Check**: State clearly whether the draft addresses the required topic, word count/scope, and deliverables.
2. **Rubric Criteria Evaluation**: Breakdown performance across the rubric criteria (e.g. Design/Concept, Implementation/ERD, Documentation).
3. **Strengths**: List 2-3 things done well.
4. **Actionable Areas for Improvement**: Point out missing rubric items or weak points to improve before final submission.
5. Maintain a constructive, supportive academic tone.
"""
        return prompt, retrieved_chunks

"""

### What You'll See in the App

* **Lecturer Mode**: Type *"Generate a database design assignment focusing on ERD diagrams and normalization"* \\(\rightarrow\\) The chatbot retrieves the module outcomes and rubrics from your documents, showing the exact source chunks retrieved, and outputs a complete assessment brief.
* **Student Mode**: Paste a draft response \\(\rightarrow\\) The chatbot retrieves the rubric criteria and outputs structured feedback on what's met, what's missing, and how to improve.

Would you like to refine any specific part of this UI or test it with one of your sample brief documents?
"""