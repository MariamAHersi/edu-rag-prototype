-- schema.sql
-- Creates the database and every table used by the prototype, so nobody has to
-- build it by hand. Safe to run more than once (nothing is dropped or overwritten).
--
-- Run it with:   mysql -u root -p < database/schema.sql
-- or open it in MySQL Workbench (File > Open SQL Script) and run it.
--
-- The columns in `assessments` match src/schema.py. If you add or remove a field
-- in schema.py, run `python src/ingest.py <folder>`: it compares schema.py with
-- the database first and prints the exact ALTER TABLE statements you need.

CREATE DATABASE IF NOT EXISTS rag_system
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE rag_system;

-- One row per assessment brief --------------------------------------------------
CREATE TABLE IF NOT EXISTS assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_file VARCHAR(255) NOT NULL UNIQUE,   -- the document this row came from
    programme VARCHAR(255),
    module_code VARCHAR(50),
    module_title VARCHAR(255),
    module_level INT,
    assessment_type VARCHAR(100),
    weighting_percent FLOAT,                    -- contribution to the module mark
    word_count INT,
    duration_minutes INT,
    deadline DATE,                              -- parsed date, NULL if only wording was given
    deadline_raw VARCHAR(255),                  -- the deadline exactly as written, e.g. 'Week 10'
    feedback_date DATE,
    feedback_date_raw VARCHAR(255),
    submission_format VARCHAR(255),
    -- long text sections (searched by the chatbot)
    task_description LONGTEXT,
    success_guidance LONGTEXT,
    layout_style_guidance LONGTEXT,
    referencing LONGTEXT,
    employability_professional_skills LONGTEXT,
    ai_use LONGTEXT,
    ethical_requirements LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_module_code (module_code),
    INDEX idx_deadline (deadline)
) ENGINE=InnoDB;

-- List-type information: one row per item ---------------------------------------
CREATE TABLE IF NOT EXISTS learning_outcomes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id INT NOT NULL,
    text TEXT,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS submission_checklist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id INT NOT NULL,
    text TEXT,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Marking criteria and their grade bands ----------------------------------------
CREATE TABLE IF NOT EXISTS criteria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id INT NOT NULL,
    name VARCHAR(255),
    description TEXT,
    weighting_percent FLOAT,
    FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- The university grade scale (reference data, seeded below).
-- These are the bands used in the Roehampton briefs; change them for another institution.
CREATE TABLE IF NOT EXISTS grade_scale (
    id INT AUTO_INCREMENT PRIMARY KEY,
    band_name VARCHAR(50) NOT NULL UNIQUE,
    min_mark INT,
    max_mark INT,
    outcome_ug VARCHAR(20),
    outcome_pg VARCHAR(20)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS grade_bands (
    id INT AUTO_INCREMENT PRIMARY KEY,
    criterion_id INT NOT NULL,
    band_name VARCHAR(100),
    descriptor TEXT,
    grade_scale_id INT NULL,                    -- optional link to grade_scale
    FOREIGN KEY (criterion_id) REFERENCES criteria(id) ON DELETE CASCADE,
    FOREIGN KEY (grade_scale_id) REFERENCES grade_scale(id)
) ENGINE=InnoDB;

INSERT IGNORE INTO grade_scale (band_name, min_mark, max_mark, outcome_ug, outcome_pg) VALUES
    ('Exemplary', 100, 100, 'Pass', 'Pass'),
    ('Outstanding', 80, 99, 'Pass', 'Pass'),
    ('Excellent', 70, 79, 'Pass', 'Pass'),
    ('Very Good', 60, 69, 'Pass', 'Pass'),
    ('Good', 50, 59, 'Pass', 'Pass'),
    ('Adequate / Fail', 40, 49, 'Pass', 'Fail'),   -- adequate at UG level, a fail at PG level
    ('Limited', 30, 39, 'Fail', 'Fail'),
    ('Limited/No Evidence', 0, 29, 'Fail', 'Fail');