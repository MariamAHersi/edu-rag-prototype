-- example_queries.sql
-- Questions a centralised assessment database can answer that scattered documents cannot.
-- Run them in MySQL Workbench or the mysql command line after ingesting some briefs.

USE rag_system;

-- 1. Assessments within a particular time (change the dates) --------------------
SELECT module_code, module_title, assessment_type, deadline, deadline_raw
FROM assessments
WHERE deadline BETWEEN '2026-01-01' AND '2026-03-31'
ORDER BY deadline;

-- 2. Assessment types across a programme ----------------------------------------
SELECT programme, assessment_type, COUNT(*) AS number_of_assessments
FROM assessments
GROUP BY programme, assessment_type
ORDER BY programme, number_of_assessments DESC;

-- 3. Modules with multiple assessments ------------------------------------------
SELECT module_code, module_title, COUNT(*) AS assessments,
       GROUP_CONCAT(assessment_type SEPARATOR ', ') AS types
FROM assessments
WHERE module_code IS NOT NULL
GROUP BY module_code, module_title
HAVING COUNT(*) > 1;

-- 4. Assessment weighting: modules whose weightings do not add up to 100% -------
--    (a module with only some of its briefs ingested will also appear here)
SELECT module_code, SUM(weighting_percent) AS total_weighting, COUNT(*) AS assessments
FROM assessments
WHERE module_code IS NOT NULL
GROUP BY module_code
HAVING SUM(weighting_percent) <> 100 OR SUM(weighting_percent) IS NULL;

-- 5. Missing assessment information: how many briefs lack each key field --------
SELECT
    COUNT(*) AS total,
    SUM(module_code IS NULL) AS no_module_code,
    SUM(programme IS NULL) AS no_programme,
    SUM(assessment_type IS NULL) AS no_type,
    SUM(weighting_percent IS NULL) AS no_weighting,
    SUM(word_count IS NULL AND duration_minutes IS NULL) AS no_length,
    SUM(deadline IS NULL) AS no_deadline_date,
    SUM(deadline IS NULL AND deadline_raw IS NULL) AS no_deadline_at_all,
    SUM(task_description IS NULL) AS no_task
FROM assessments;

-- 5b. Which briefs have gaps (including empty rubrics and learning outcomes) ----
SELECT a.id, a.source_file,
    (SELECT COUNT(*) FROM criteria c WHERE c.assessment_id = a.id) AS criteria,
    (SELECT COUNT(*) FROM learning_outcomes l WHERE l.assessment_id = a.id) AS outcomes,
    a.deadline IS NULL AS no_deadline_date,
    a.weighting_percent IS NULL AS no_weighting,
    a.task_description IS NULL AS no_task
FROM assessments a
ORDER BY criteria, outcomes;

-- 6. Deadlines that are close together (within 7 days, same programme) ----------
SELECT a.module_code AS module_a, a.assessment_type AS type_a, a.deadline AS deadline_a,
       b.module_code AS module_b, b.assessment_type AS type_b, b.deadline AS deadline_b,
       ABS(DATEDIFF(b.deadline, a.deadline)) AS days_apart
FROM assessments a
JOIN assessments b
  ON a.id < b.id
 AND ABS(DATEDIFF(b.deadline, a.deadline)) <= 7
 AND a.programme <=> b.programme
ORDER BY a.deadline;

-- 7. A centralised assessment calendar -------------------------------------------
SELECT module_code, assessment_type, COALESCE(deadline_raw, deadline) AS deadline, weighting_percent
FROM assessments
ORDER BY deadline IS NULL, deadline;