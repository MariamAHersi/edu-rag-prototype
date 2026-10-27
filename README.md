# Centralised University Assessment Database

A prototype relational database developed during my **Data Analyst – Digital Repository Internship at the University of Roehampton**.

The project explores how information contained within university assessment briefs can be extracted, standardised and stored in a centralised relational database.

The database is designed to provide a structured foundation for future applications involving assessment management, student support, curriculum analysis, educational analytics and AI.

---

## 🎯 Project Aim

The main aim of this project is to explore the feasibility of creating a **centralised database of university assessment information**.

Assessment information is often distributed across individual documents, making it difficult to obtain a consistent overview across modules, programmes or departments.

This project addresses this by extracting key information from assessment briefs and converting it into a structured format using a **Pydantic schema** before storing it in a relational database.

The project explores how this centralised dataset could eventually support questions such as:

- What assessments are taking place across different modules?
- When are students' upcoming deadlines?
- Are multiple assessments clustered around the same period?
- How do assessment types and requirements vary between modules?
- Are assessment briefs consistent across different modules or departments?
- Could assessment data identify wider issues with modules, teaching or assessment design?
- Could additional academic data be combined with assessment information to identify areas where students may be struggling?
- Could students have a centralised view of their assessment deadlines and requirements?
- Could the database provide a foundation for future AI-supported applications?

The current project focuses on **building the data foundation**, rather than implementing all of these potential applications.

---

# 🏗️ Project Architecture

The current workflow is:

```text
University Assessment Briefs
          ↓
Document Extraction
          ↓
Pydantic Data Validation
          ↓
Structured Assessment Records
          ↓
Relational Database
          ↓
Future Applications
```

The database is designed to separate the **data layer** from potential applications that may be built on top of it.

For example:

```text
                    ┌──────────────────────┐
                    │ Assessment Briefs    │
                    │ PDF / DOCX           │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Document Processing  │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Pydantic Schema      │
                    │ Validation           │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Relational Database  │
                    │ MySQL                │
                    └──────────┬───────────┘
                               ↓
          ┌────────────────────┼────────────────────┐
          ↓                    ↓                    ↓
    Student Tools       Staff Analytics       AI Applications
```

---

# 📊 Data Extraction

Assessment briefs contain information in different formats and layouts. The project therefore uses a structured **Pydantic schema** to standardise the information extracted from each document.

The current schema captures information such as:

| Field | Description |
|---|---|
| Programme | Programme associated with the assessment |
| Module | Module associated with the assessment |
| Level | Academic level |
| Assessment Type | Type of assessment |
| Weight | Percentage contribution to the module |
| Word Count | Required word count where applicable |
| Duration | Assessment duration where applicable |
| Deadline | Assessment deadline |
| Submission Format | Required submission format |
| Feedback | Information about feedback |
| Source File | Original document used to create the record |

The schema can be modified depending on the requirements of future projects.

---

# 🗄️ Relational Database

The extracted information is stored in a **MySQL relational database**.

A relational database was selected because the project requires structured, consistent and queryable information that can eventually be related across:

- Modules
- Programmes
- Assessments
- Departments
- Assessment types
- Deadlines
- Assessment requirements

The database can therefore act as a **single structured source of assessment information** rather than requiring applications to repeatedly process the original documents.

---

# 🚀 Recreating the Database for a Future University Project

The database structure is designed to be reusable for future university projects.

The following process can be used to recreate the database using a new collection of assessment briefs.

## 1. Collect the assessment documents

Create a directory containing the assessment briefs you want to process.

For example:

```text
assessment_briefs/
├── module_a_brief.pdf
├── module_b_brief.pdf
├── module_c_brief.docx
└── module_d_brief.pdf
```

Only use documents that you are authorised to process.

---

## 2. Extract the document content

Use the document-processing scripts to extract text and/or tables from the assessment briefs.

The project currently supports documents such as:

- PDF
- DOCX

The extraction process should preserve as much of the original assessment information as possible.

---

## 3. Define the data schema

Create or modify the Pydantic schema according to the information that needs to be captured.

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

The schema acts as a standard structure for converting different assessment documents into consistent records.

---

## 4. Validate the extracted information

Before inserting records into the database, validate the extracted information against the Pydantic schema.

This helps identify:

- Missing information
- Incorrect data types
- Unexpected values
- Inconsistent formatting

Validation is particularly important when processing assessment briefs created by different people or departments.

---

## 5. Create the MySQL database

Create a MySQL database for the project.

For example:

```sql
CREATE DATABASE assessment_repository;
```

Then create the required tables according to the project's database schema.

The database structure can be adapted depending on the requirements of the new university or department.

---

## 6. Configure the database connection

The Python application connects to MySQL using `mysql.connector`.

Database credentials should be stored using environment variables rather than directly inside the source code.

For example:

```text
DB_HOST=localhost
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=assessment_repository
```

**Do not commit passwords, API keys or other credentials to GitHub.**

---

## 7. Insert the structured records

Once the documents have been processed and validated, the resulting records can be inserted into the MySQL database.

The database should retain a reference to the original source document where possible.

For example:

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

---

## 8. Query the database

Once populated, the database can be queried using SQL.

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

This could provide a foundation for creating a centralised assessment calendar or dashboard.

Other possible queries could investigate:

```sql
-- Assessments taking place within a particular period

-- Assessment types used across a programme

-- Modules with multiple assessments

-- Assessment weighting across modules

-- Missing assessment information

-- Assessment deadlines clustered around the same period
```

---

# 💡 Potential Applications

The database itself is not intended to be the final product. Instead, it provides a structured foundation that future applications can build upon.

## 👩‍🎓 Student Applications

A student-facing application could provide a centralised view of assessment information across their modules.

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

Potential functionality could include:

- Upcoming deadlines
- Assessment requirements
- Submission formats
- Assessment weighting
- Assessment types
- Workload planning
- Identifying clusters of deadlines
- Comparing assessment requirements across modules

---

## 👩‍🏫 Academic and Staff Applications

The database could also support staff-facing analysis.

Potential applications include:

- Comparing assessment structures across modules
- Reviewing assessment types
- Identifying assessment workload patterns
- Checking consistency between assessment briefs
- Identifying missing or unclear assessment information
- Supporting curriculum review
- Analysing assessment design across programmes

---

## 📈 Educational Analytics

The structured assessment data could potentially be combined with other university datasets to investigate wider academic issues.

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

This could eventually help investigate questions such as:

- Are assessments clustered within particular periods?
- Are some assessment types associated with particular outcomes?
- Are there recurring issues across assessment briefs?
- Are there patterns in student performance?
- Are there particular areas where students may require additional support?

These applications would require appropriate additional data and permissions and are **outside the scope of the current prototype**.

---

# 🤖 Potential AI Applications

The structured database could also provide a foundation for future AI applications.

For example, a future RAG or AI assistant could retrieve assessment information from the database rather than repeatedly processing individual documents.

Possible applications include:

- Answering questions about assessment requirements
- Finding relevant assessment information
- Comparing assessment briefs
- Identifying similarities between assessments
- Summarising assessment requirements
- Supporting staff in reviewing assessment documentation

The previous RAG exploration in this project therefore represents **one potential application of the centralised data**, rather than the primary purpose of the database.

---

# 🔬 Research and Further Investigation

The project also considers research around:

- Assessment workload and deadline clustering
- Educational and learning analytics
- Centralised educational data
- Assessment design
- Student access to assessment information
- AI applications in higher education
- Data privacy and security
- Ethical use of educational data

The research is used to explore how a centralised assessment database could potentially support students, academics and the wider institution.

---

# 🧪 Testing and Evaluation

When recreating the database with a new collection of documents, the extraction process should be evaluated for:

### Data accuracy

Does the extracted information accurately represent the original assessment brief?

### Data completeness

Are important fields missing?

### Consistency

Are similar pieces of information represented in the same format across different documents?

### Scalability

Can the system process assessment briefs from multiple modules and departments?

### Adaptability

Can the schema accommodate different assessment types and document structures?

### Database integrity

Are the records correctly inserted and stored without duplication or data loss?

---

# ⚠️ Limitations

The current prototype has several limitations.

### Document variation

Assessment briefs may use different layouts, terminology and structures, making consistent extraction difficult.

### Missing information

Some assessment briefs may not contain all of the fields defined by the database schema.

### Data quality

The quality of the database depends on the accuracy and consistency of the original documents.

### Scope

The current prototype focuses primarily on assessment information and does not provide a complete picture of student academic experience.

### AI limitations

Any future AI functionality would need to consider hallucinations, retrieval accuracy, bias, privacy and security.

### Student data

The current project does not attempt to make conclusions about individual students. More sensitive student-level analysis would require additional data, appropriate permissions and robust data protection measures.

---

# 🛠️ Technologies

The project uses technologies including:

- **Python**
- **Pydantic** – data validation and structured schemas
- **MySQL** – relational database
- **mysql-connector-python** – database connectivity
- **PDF/DOCX processing libraries** – document extraction
- **SQL** – querying and managing structured data
- **Git/GitHub** – version control

Additional technologies may be used for future applications built on top of the database.

---

# 📁 Project Structure

A simplified version of the project structure is:

```text
rag-assessment-repository/
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

The exact structure may change as the prototype develops.

---

# ▶️ Running the Project

Clone the repository:

```bash
git clone <repository-url>
```

Navigate into the project:

```bash
cd rag-assessment-repository
```

Create a Python environment:

```bash
python -m venv .venv
```

Activate the environment on Windows:

```bash
.venv\Scripts\activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Configure the required database environment variables.

Then run the relevant document-processing and database scripts.

If the optional Streamlit prototype is included, it can be launched with:

```bash
streamlit run app.py
```

---

# 🎓 Internship Context

This project was developed as part of my **Data Analyst – Digital Repository Internship at the University of Roehampton**.

The wider project explores how a centralised repository of university materials could improve access to educational and assessment information within the Computing Department.

The focus of this prototype is the **structured storage of assessment information**, providing a foundation for future student-facing, academic and analytical applications.

---

# 🚧 Project Status

**Status: Prototype / In Development**

The current project demonstrates the extraction, validation and storage of assessment information in a relational database.

It is **not a production-ready university system**.

Future implementations would require further work around:

- Data governance
- Authentication and authorisation
- Data protection
- Database security
- Data quality
- Scalability
- User testing
- Integration with existing university systems
- Institutional approval

---

# 🔮 Future Development

Potential future development includes:

- Expanding the database schema
- Processing assessment briefs from additional departments
- Improving document extraction
- Developing a student assessment dashboard
- Creating assessment deadline visualisations
- Analysing assessment workload and deadline clustering
- Comparing assessment structures across modules
- Integrating additional university datasets
- Developing AI-supported search and analysis
- Exploring Moodle integration
- Adding authentication and access controls
- Conducting user testing with students and academics
- Evaluating privacy, security and ethical considerations

---

# 📌 Data Protection and Responsible Use

University assessment documents and educational data may contain sensitive or restricted information.

Anyone recreating or extending this project should:

- Only use documents they are authorised to access
- Avoid committing confidential documents to GitHub
- Avoid storing personally identifiable student information unnecessarily
- Keep database credentials and API keys outside the repository
- Follow the relevant university data protection and governance requirements
- Obtain appropriate permissions before processing student-level data

The repository should therefore be treated as a **technical prototype and framework for experimentation**, rather than a system approved for handling production university data.