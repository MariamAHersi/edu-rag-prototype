#%%
import json
from pathlib import Path
from embedder import SimpleVectorStore  

#%%
class LecturerBriefGenerator:

    def __init__(self, vector_store: SimpleVectorStore):
        """Initializes the generator with our trained vector store."""
        self.store = vector_store

    def build_grounded_prompt(
        self,
        lecturer_request: str,
        module_code: str = "CMP020C106S",
        top_k: int = 5,
    ) -> tuple[str, list[dict]]:
        """Retrieves institutional context and builds a grounded prompt for the LLM."""
        # 1. Retrieve relevant module standards, outcomes, and policies
        search_query = f"{module_code} {lecturer_request} learning outcomes marking criteria AI guidance"
        retrieved_chunks = self.store.retrieve(search_query, top_k=top_k)

        # 2. Format retrieved context with source attribution
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            context_blocks.append(
                f"--- Context Chunk [{idx}] (Source: {chunk['source_file']} | Section: {chunk['section']}) ---\n"
                f"{chunk['content']}\n"
            )

        context_str = "\n".join(context_blocks)

        # 3. Construct system prompt with strict grounding constraints
        system_prompt = f"""You are an Academic Brief Generation Assistant for university lecturers.
Your job is to generate a comprehensive, professional Assessment Brief based on the Lecturer's Request.

### MANDATORY INSTITUTIONAL CONTEXT (RETRIEVED FROM MODULE REPOSITORY):
{context_str}

### INSTRUCTIONS FOR GENERATING THE BRIEF:
1. Ensure the brief aligns directly with the retrieved Learning Outcomes and Employability Skills.
2. Incorporate the required submission deliverables (e.g. word counts, file formats, team/individual rules).
3. Include clear marking criteria and grade descriptor expectations (Excellent, Satisfactory, Not Satisfactory).
4. Include the mandatory institutional policies regarding Artificial Intelligence (AI) and Referencing.
5. Format the entire brief clearly using Markdown headers and tables.

### LECTURER REQUEST:
{lecturer_request}

Generate the complete Assessment Brief now:
"""
        return system_prompt, retrieved_chunks

    def generate_brief_mock(self, lecturer_request: str) -> str:
        """Runs retrieval and returns a structured brief demonstrating the grounded output."""
        prompt, chunks = self.build_grounded_prompt(lecturer_request)

        print(
            f"[RAG Engine] Retrieved {len(chunks)} relevant chunks from module docs."
        )
        for c in chunks:
            print(
                f" -> Score: {c['similarity_score']} | Source: {c['source_file']} ({c['section']})"
            )

        return prompt

# --- Test Execution ---
if __name__ == "__main__":
    store = SimpleVectorStore()
    store.load_index()

    generator = LecturerBriefGenerator(store)

    request = "Create a database project brief for Level 4 students requiring an ERD diagram with 12-14 entities, physical schema, and individual/group submission guidelines."
    prompt = generator.generate_brief_mock(request)

    print("\n=================== GENERATED GROUNDED PROMPT ===================")
    print(prompt[:1500] + "\n\n... [Prompt truncated for display] ...")