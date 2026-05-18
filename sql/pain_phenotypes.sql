-- ED pain assessments for acute pancreatitis and trauma cohorts (MIMIC-IV ED + hosp).
-- Run via scripts/fetch_pain_data.py against PhysioNet BigQuery (physionet-data).

WITH Background AS (
    SELECT
        e.subject_id,
        e.stay_id,
        e.intime,
        e.outtime,
        e.gender,
        CASE
            WHEN UPPER(e.race) IN ('UNKNOWN', 'UNABLE TO OBTAIN', 'PATIENT DECLINED TO ANSWER', 'OTHER') THEN 'Unknown'
            WHEN UPPER(e.race) = 'PORTUGUESE' THEN 'White'
            WHEN UPPER(e.race) = 'SOUTH AMERICAN' THEN 'Hispanic/Latino'
            WHEN UPPER(e.race) = 'MULTIPLE RACE/ETHNICITY' THEN 'Two or More Races'
            WHEN UPPER(e.race) = 'AMERICAN INDIAN/ALASKA NATIVE' THEN 'American Indian or Alaska Native'
            WHEN UPPER(e.race) = 'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER' THEN 'Native Hawaiian or Other Pacific Islander'
            WHEN LOWER(e.race) LIKE '%asian%' THEN 'Asian'
            WHEN LOWER(e.race) LIKE '%black%' OR LOWER(e.race) LIKE '%african%' THEN 'Black/African'
            WHEN LOWER(e.race) LIKE '%white%' THEN 'White'
            WHEN LOWER(e.race) LIKE '%hispanic%' THEN 'Hispanic/Latino'
            ELSE 'Other'
        END AS race_group,
        e.arrival_transport,
        e.disposition
    FROM
        `physionet-data.mimiciv_ed.edstays` e
),
PatientAge AS (
    SELECT
        subject_id,
        anchor_age AS age
    FROM
        `physionet-data.mimiciv_3_1_hosp.patients`
),
Demographics AS (
    SELECT
        a.subject_id,
        a.admission_type,
        a.admit_provider_id,
        a.admission_location,
        a.insurance,
        a.language,
        a.marital_status,
        a.hospital_expire_flag
    FROM
        `physionet-data.mimiciv_3_1_hosp.admissions` a
),
Vitals AS (
    SELECT
        subject_id,
        stay_id,
        charttime,
        pain        AS pain_score,
        temperature,
        heartrate,
        resprate,
        o2sat,
        sbp,
        dbp
    FROM
        `physionet-data.mimiciv_ed.vitalsign`
    WHERE
        pain IS NOT NULL
),
Diagnoses AS (
    SELECT
        d.subject_id,
        d.stay_id,
        d.icd_code,
        d.icd_version,
        d.icd_title,
        CASE
            WHEN LOWER(d.icd_title) LIKE '%acute pancreatitis%' THEN 'acute_pancreatitis'
            WHEN d.icd_code BETWEEN 'S00' AND 'T88' THEN 'trauma'
        END AS diagnosis_group,
        ROW_NUMBER() OVER (
            PARTITION BY d.subject_id, d.stay_id
            ORDER BY
                CASE
                    WHEN LOWER(d.icd_title) LIKE '%acute pancreatitis%' THEN 0
                    ELSE 1
                END
        ) AS rn
    FROM
        `physionet-data.mimiciv_ed.diagnosis` d
    WHERE
        LOWER(d.icd_title) LIKE '%acute pancreatitis%'
        OR d.icd_code BETWEEN 'S00' AND 'T88'
)
SELECT
    b.subject_id,
    b.stay_id,
    b.intime,
    b.outtime,
    b.gender,
    b.race_group AS race,
    pa.age,
    vs.charttime    AS pain_charttime,
    vs.pain_score,
    vs.temperature,
    vs.heartrate,
    vs.resprate,
    vs.o2sat,
    vs.sbp,
    vs.dbp,
    d.icd_code,
    d.icd_title,
    d.diagnosis_group,
    a.admission_type,
    a.admit_provider_id,
    a.admission_location,
    a.insurance,
    a.language,
    a.marital_status,
    a.hospital_expire_flag
FROM
    Background b
LEFT JOIN
    Vitals vs ON b.subject_id = vs.subject_id
           AND b.stay_id = vs.stay_id
LEFT JOIN
    PatientAge pa ON b.subject_id = pa.subject_id
LEFT JOIN
    Diagnoses d ON b.subject_id = d.subject_id
              AND b.stay_id = d.stay_id
              AND d.rn = 1
LEFT JOIN
    Demographics a ON b.subject_id = a.subject_id
WHERE
    vs.pain_score IS NOT NULL
    AND d.icd_code IS NOT NULL
ORDER BY
    b.subject_id, b.stay_id, vs.charttime;
