# Centralised University Assessment Database

A prototype relational database developed during my **Data Analyst – Digital Repository Internship at the University of Roehampton**.

The project looks at how information from university assessment briefs can be extracted, organised and stored in one central database.

The idea is to make assessment information easier to work with and provide a base for things like assessment calendars, staff analysis, student tools and future AI applications.

---

## Project Aim

The main aim of this project is to explore whether assessment information from different university documents can be brought together into one structured database.

At the moment, assessment information can be spread across different documents and modules. This makes it harder to get an overview of things such as assessment types, deadlines, weightings and requirements.

For this prototype, I extract information from assessment briefs, validate it using a **Pydantic schema**, and then store it in a **MySQL relational database**.

Some of the questions this could eventually help answer are:

- What assessments are taking place across different modules?
- When are students' upcoming deadlines?
- Are several assessments taking place around the same time?
- How do assessment types and requirements differ between modules?
- Are there differences in how assessment briefs are structured?
- Can assessment data be used to support curriculum or assessment review?
- Could additional university data be combined with assessment data to identify areas where students may need more support?
- Could students have one place to view their assessment deadlines and requirements?
- Could the database be used as the basis for future AI tools?

The current project focuses on **building the database and data structure**, rather than implementing all of these ideas.

---

# How It Works

The current process is:

```text
Assessment Briefs
       ↓
Document Extraction
       ↓
Pydantic Validation
       ↓
Structured Assessment Data
       ↓
MySQL Database
       ↓
Future Applications
```

The main idea is to keep the assessment data separate from any application that might use it later.

For example:

```text
        Assessment Briefs
          PDF / DOCX
               ↓
       Document Processing
               ↓
        Pydantic Schema
          & Validation
               ↓
        MySQL Database
               ↓
      ┌────────┼────────┐
      ↓        ↓        ↓
   Student    Staff     AI
    Tools    Analysis  Tools
```

This means that future applications would not need to repeatedly process the original assessment documents.

---

# Data Extraction

Assessment briefs do not all follow the same format, so the project uses a **Pydantic model** to give the extracted information a consistent structure.

The current schema includes:

| Field | Description |
|---|---|
| Programme | Programme linked to the assessment |
| Module | Module linked to the assessment |
| Level | Academic level |
| Assessment Type | Type of assessment |
| Weighting | Percentage contribution to the module |
| Word Count | Required word count |
| Duration | Assessment duration where applicable |
| Deadline | Assessment deadline |
| Submission Format | Required submission format |
| Feedback | Information about feedback |
| Source File | Original document |

The schema can be changed depending on what information a future project needs.

For example:

```python
class AssessmentBrief(BaseModel):
    programme: str | None
    module: str | None
    level: str | None
    assessment_type: str | None
    weighting: float | None
    word_count: str | None
    duration: str | None
    deadline: str | None
    submission_format: str | None
    feedback: str | None
    source_file: str
```

Using a schema also makes it easier to spot missing or incorrectly formatted information before it is added to the database.

---

# MySQL Database

The extracted information is stored in a **MySQL relational database**.

A relational database was used because the information is structured and can be queried and related across things such as:

- Modules
- Programmes
- Assessments
- Assessment types
- Deadlines
- Assessment requirements

The database can therefore act as one structured place for assessment information instead of having to search through individual documents each time.

---

# Recreating the Database

One of the aims of the project is for the database structure to be reusable if the project is continued or used with another collection of university documents.

The basic process is:

### 1. Collect the assessment documents

Place the assessment briefs you want to process into a folder.

For example:

```text
assessment_briefs/
├── module_a_brief.pdf
├── module_b_brief.pdf
├── module_c_brief.docx
└── module_d_brief.pdf
```

Only use documents that you have permission to process.

### 2. Extract the document content

The document processing code extracts information from the assessment briefs.

The current prototype works with:

- PDF
- DOCX

The aim is to keep as much useful information from the original documents as possible.

### 3. Create or update the schema

The Pydantic model defines the information that should be stored.

The fields can be changed depending on the requirements of the project.

### 4. Validate the data

The extracted information is checked against the Pydantic model before being added to MySQL.

This helps identify things such as:

- Missing information
- Incorrect data types
- Unexpected values
- Inconsistent formatting

This is particularly useful when assessment briefs come from different modules or departments.

### 5. Create the MySQL database

For example:

```sql
CREATE DATABASE assessment_repository;
```

The required tables can then be created based on the database design.

### 6. Set up the database connection

The Python code uses `mysql-connector-python` to connect to MySQL.

Database credentials should be kept outside the code using environment variables.

For example:

```text
DB_HOST=localhost
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=assessment_repository
```

Do not commit passwords, API keys or other credentials to GitHub.

### 7. Insert the data

Once the documents have been extracted and validated, the structured records can be inserted into MySQL.

The original source file is also kept with the record so that the database entry can be traced back to the document it came from.

```text
Assessment Brief
       ↓
Extract information
       ↓
Validate with Pydantic
       ↓
Create structured record
       ↓
Insert into MySQL
```

### 8. Query the database

Once the data is stored, SQL can be used to retrieve information.

For example:

```sql
SELECT
    module,
    assessment_type,
    deadline,
    weighting
FROM assessments
ORDER BY deadline;
```

This could be used to create something like a centralised assessment calendar.

Other queries could look at:

- Assessments within a particular time period
- Assessment types across a programme
- Modules with multiple assessments
- Assessment weighting
- Missing assessment information
- Deadlines that are close together

---

# Potential Applications

The database is the main part of this prototype, but there are several things that could potentially be built on top of it.

## Student Applications

A student-facing application could bring assessment information from different modules into one place.

For example:

```text
My Assessments

Data Science
└── Coursework
    Deadline: 12 November
    Weighting: 40%

Artificial Intelligence
└── Project
    Deadline: 18 November
    Weighting: 50%

Software Development
└── Report
    Deadline: 25 November
    Weighting: 30%
```

Possible features could include:

- Upcoming deadlines
- Assessment requirements
- Submission formats
- Assessment weighting
- Assessment types
- Workload planning
- Identifying clusters of deadlines
- Comparing requirements across modules

---

## Staff Applications

The same data could also be useful for academic and professional staff.

For example:

- Comparing assessment structures across modules
- Looking at the types of assessment being used
- Identifying periods with a high number of assessments
- Checking consistency between assessment briefs
- Finding missing or unclear information
- Supporting curriculum review
- Looking at assessment design across programmes

---

# Educational Analytics

The assessment database could eventually be combined with other university data.

For example:

```text
Assessment Data
      +
Module Data
      +
Student Performance Data
      +
Feedback Data
      ↓
Educational Analytics
```

This could allow the university to investigate questions such as:

- Are assessments clustered around particular periods?
- Are there recurring issues with assessment briefs?
- Are there patterns in student performance?
- Are there particular areas where students may need additional support?

However, the current database **cannot answer all of these questions on its own**. Student performance and other academic data would need to be added, along with the appropriate permissions and data protection measures.

---

# AI and RAG

The structured database could also be used for future AI applications.

For example, an AI assistant could retrieve assessment information from the database instead of having to process individual documents each time.

Possible uses include:

- Answering questions about assessment requirements
- Finding relevant assessment information
- Comparing assessment briefs
- Finding similarities between assessments
- Summarising assessment requirements
- Helping staff review assessment documentation

I previously explored a **RAG-based approach** as part of this project. The database changes the role of that work slightly. Rather than the RAG system being the main project, it can be treated as **one possible application of the centralised assessment data**.

---

# Research and Further Investigation

Some of the areas I am interested in exploring further include:

- Assessment workload and deadline clustering
- Educational and learning analytics
- Centralising educational data
- Assessment design
- Student access to assessment information
- AI in higher education
- Data privacy and security
- Ethical use of educational data

The research helps explore whether a centralised assessment database could actually be useful to students, academics and the wider university.

---

# Testing and Evaluation

If the project is continued with more assessment briefs, I would evaluate it based on:

### Data accuracy

Does the extracted information match the original assessment brief?

### Data completeness

Are important fields missing?

### Consistency

Are similar pieces of information stored in a consistent way?

### Scalability

Can the process handle assessment briefs from more modules and departments?

### Adaptability

Can the schema handle different assessment types and document formats?

### Database integrity

Are records stored correctly without unnecessary duplication or data loss?

---

# Limitations

There are currently a few limitations to the prototype.

### Different document formats

Assessment briefs can have very different layouts, wording and structures. This can make automated extraction difficult.

### Missing information

Not every assessment brief will contain all of the fields in the database.

### Data quality

The quality of the database depends on the quality and consistency of the original documents.

### Scope

The current prototype focuses on assessment information. It does not provide a complete picture of a student's academic experience.

### AI

Any future AI functionality would need to consider things such as hallucinations, retrieval accuracy, bias, privacy and security.

### Student data

The current project does not make conclusions about individual students. Any future work involving student-level data would need additional permissions and appropriate data protection measures.

---

# Technologies

The project currently uses:

- **Python**
- **Pydantic** – data validation and structured schemas
- **MySQL** – relational database
- **mysql-connector-python** – connecting Python to MySQL
- **PyMuPDF / pdfplumber** – PDF processing
- **python-docx** – DOCX processing
- **Google Gemini API** – extracting structured information from assessment documents
- **Sentence Transformers** – embeddings / previous RAG work
- **SQL** – querying the database
- **Git/GitHub** – version control
- **Streamlit** – prototype interface
- **Jupyter** – document exploration and testing

---

# Project Structure

The project is still being developed, so the structure may change.

A simplified version is:

```text
edu-rag-prototype/
│
├── assessment_briefs/
│   ├── raw_docs/
│   └── extracted_docs/
│
├── notebooks/
│   └── document_exploration.ipynb
│
├── src/
│   ├── document_processing/
│   ├── database/
│   ├── embeddings/
│   ├── retrieval/
│   └── rag/
│
├── tests/
│
├── requirements.txt
└── README.md
```

---

# Running the Project

Clone the repository:

```bash
git clone <repository-url>
```

Move into the project folder:

```bash
cd edu-rag-prototype
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Set up the required database environment variables before running the ingestion code.

The relevant document-processing and database scripts can then be run from the project.

If the Streamlit prototype is included:

```bash
streamlit run app.py
```

---

# Internship Context

This project was developed as part of my **Data Analyst – Digital Repository Internship at the University of Roehampton**.

The wider internship project looks at how university materials could be organised and made easier to access within the Computing Department.

My work has focused on assessment information and how it could be extracted from existing documents and stored in a more structured way.

---

# Project Status

**Status: Prototype / In Development**

The current prototype demonstrates the process of:

```text
Assessment Documents
        ↓
Data Extraction
        ↓
Validation
        ↓
MySQL Database
```

It is **not a production university system**.

A production version would need further work around:

- Data governance
- Authentication and access control
- Data protection
- Database security
- Data quality
- Scalability
- User testing
- Integration with existing university systems
- Institutional approval

---

# Future Development

Some possible next steps are:

- Add more assessment briefs
- Expand the database schema
- Improve document extraction
- Process documents from other departments
- Build a student assessment dashboard
- Create assessment deadline visualisations
- Analyse assessment workload and deadline clustering
- Compare assessment structures across modules
- Connect other university datasets
- Explore AI-supported search and analysis
- Explore Moodle integration
- Add authentication and access controls
- Test the system with students and academics
- Further investigate privacy, security and ethical considerations

---

# Data Protection

University documents and educational data may contain information that should not be publicly shared.

Anyone continuing this project should:

- Only use documents they are authorised to access
- Avoid committing confidential documents to GitHub
- Avoid storing student information unnecessarily
- Keep passwords and API keys outside the repository
- Follow the relevant university data protection requirements
- Get the appropriate permissions before working with student-level data

This repository should therefore be treated as a **prototype for development and experimentation**, rather than a production university system.