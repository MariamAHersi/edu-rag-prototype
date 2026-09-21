# AI-Powered Assessment Repository

A prototype Retrieval-Augmented Generation (RAG) system developed during my **Data Analyst – Digital Repository Internship at the University of Roehampton**.

The project explores how AI and semantic search can be used to improve access to assessment information within the Computing Department, helping students and educators find relevant information from module documentation such as assessment briefs, learning outcomes and marking criteria.

## 🎯 Project Aim

The aim of this project is to explore how a centralised digital repository combined with a RAG system could make assessment information easier to access and use.

The system is being developed as a prototype to investigate questions such as:

* How can students quickly find relevant information about their assessments?
* Can an AI assistant provide answers based on university-approved documents?
* How can retrieval reduce hallucinations compared with relying only on an LLM?
* How could the system support both students and educators?
* What are the privacy, security and bias considerations when using AI with educational data?

## 🏗️ Proposed System

The basic workflow is:

```text
University Documents
       ↓
Document Processing
       ↓
Text Extraction
       ↓
Chunking
       ↓
Embeddings
       ↓
Vector Database
       ↓
Semantic Search
       ↓
Relevant Context
       ↓
LLM / RAG System
       ↓
AI Response
```

The system retrieves relevant information from the assessment documents before generating a response. This helps ground the AI's answers in the information contained within the university documents.

## 📚 Documents

The prototype currently focuses on assessment-related documents, including:

* Assessment briefs
* Module outlines
* Learning outcomes
* Assessment criteria
* Marking rubrics
* Other relevant module documentation

## 🔎 RAG Approach

The project investigates **Retrieval-Augmented Generation (RAG)** rather than relying solely on an LLM.

The general process is:

1. Load university documents.
2. Extract the text from the documents.
3. Split the text into smaller chunks.
4. Convert the chunks into embeddings.
5. Store the embeddings in a searchable vector database.
6. Convert a user's question into an embedding.
7. Retrieve the most relevant document sections.
8. Provide the retrieved information to the LLM.
9. Generate an answer based on the retrieved context.

This approach is intended to make responses more relevant and reduce the likelihood of unsupported or inaccurate answers.

## 🧪 Current Prototype

The repository is currently a **work-in-progress prototype**.

Current areas of development include:

* [x] Research into RAG and semantic search
* [x] Research into AI applications in higher education
* [x] Extract text from PDF assessment briefs
* [x] Extract text from Word documents
* [ ] Implement document chunking
* [ ] Generate embeddings
* [ ] Implement semantic search
* [ ] Build the RAG pipeline
* [ ] Connect an LLM
* [ ] Evaluate response accuracy
* [ ] Explore a Moodle-based interface
* [ ] Investigate student and educator use cases

## 💡 Potential Use Cases

### Student-facing

A potential student interface could allow students to ask questions such as:

> "What are the requirements for this assessment?"

> "What learning outcomes does this assignment assess?"

> "What are the marking criteria?"

> "What should I include in my submission?"

The system would retrieve information from the relevant university documents before generating a response.

### Educator-facing

A future educator interface could potentially support:

* Creating or reviewing assessment briefs
* Checking alignment between briefs and learning outcomes
* Identifying unclear assessment requirements
* Analysing common issues in student submissions
* Providing insights into assessment performance

## ⚠️ AI Challenges

The project also considers several challenges associated with using AI in education.

### Hallucinations

LLMs can generate information that is not supported by the source documents. RAG can help reduce this risk by grounding responses in retrieved university content, but it does not completely eliminate hallucinations.

### Retrieval Accuracy

Poor semantic search results can lead to the LLM receiving irrelevant context and consequently producing an inaccurate answer.

### Bias

AI-generated feedback may introduce or reproduce biases within assessment and educational data.

### Privacy and Security

Student and university data must be handled carefully. Any future implementation would need to consider data protection, access control and appropriate handling of sensitive information.

### Over-contextualisation

Providing too much irrelevant information to the model can potentially make responses less accurate. The project therefore explores how relevant context can be retrieved without overwhelming the model.

## 🛠️ Technologies

The technologies used in the prototype may include:

* Python
* RAG
* Semantic Search
* Embeddings
* Large Language Models (LLMs)
* PDF/Word document processing
* Vector databases
* APIs

Specific tools and frameworks will be documented as the prototype develops.

## 🎓 Internship Context

This project is being developed as part of my **Data Analyst – Digital Repository Internship at the University of Roehampton**.

The wider project explores how a centralised digital repository could improve how students and lecturers access educational and assessment content within the Computing Department.

This GitHub repository documents the technical exploration and prototype development process.

## 🚧 Project Status

**Status: Prototype / In Development**

This repository is primarily intended to document the development, experimentation and evaluation of the RAG system.

It should not be considered a production-ready university system.

## 🔮 Future Development

Potential future work includes:

* Improving document parsing and cleaning
* Testing different embedding models
* Comparing semantic search approaches
* Evaluating different chunking strategies
* Improving retrieval accuracy
* Adding citations to retrieved sources
* Evaluating LLM responses against assessment documents
* Developing a user interface
* Exploring Moodle integration
* Investigating authentication and access control
* Conducting user testing with students and educators
* Evaluating privacy, security and ethical considerations

## 📌 Note

The documents and data used in this repository should not contain confidential or personally identifiable student information.

Where university materials are used for experimentation, appropriate permissions and data protection requirements should be followed.
