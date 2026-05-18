WITH ed_base AS (
    SELECT
        e.subject_id,
        e.stay_id,
        e.hadm_id,
        e.intime,
        e.outtime,
        DATETIME_DIFF(e.outtime, e.intime, MINUTE) AS ed_los_minutes,
        e.gender AS sex,
        e.race AS race_raw,
        CASE
            WHEN UPPER(e.race) IN ('UNKNOWN', 'UNABLE TO OBTAIN', 'PATIENT DECLINED TO ANSWER', 'OTHER') THEN 'Unknown'
            WHEN UPPER(e.race) = 'PORTUGUESE' THEN 'White'
            WHEN UPPER(e.race) = 'SOUTH AMERICAN' THEN 'Hispanic'
            WHEN UPPER(e.race) = 'MULTIPLE RACE/ETHNICITY' THEN 'Two or More Races'
            WHEN UPPER(e.race) = 'AMERICAN INDIAN/ALASKA NATIVE' THEN 'American Indian or Alaska Native'
            WHEN UPPER(e.race) = 'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER' THEN 'Native Hawaiian or Other Pacific Islander'
            WHEN LOWER(e.race) LIKE '%asian%' THEN 'Asian'
            WHEN LOWER(e.race) LIKE '%black%' OR LOWER(e.race) LIKE '%african%' THEN 'Black'
            WHEN LOWER(e.race) LIKE '%white%' THEN 'White'
            WHEN LOWER(e.race) LIKE '%hispanic%' OR LOWER(e.race) LIKE '%latino%' THEN 'Hispanic'
            ELSE 'Other'
        END AS race_ethnicity,
        e.arrival_transport,
        e.disposition,
        CASE
            WHEN UPPER(e.disposition) = 'HOME' THEN 'HOME'
            WHEN UPPER(e.disposition) = 'ADMITTED' THEN 'ADMITTED'
            WHEN UPPER(e.disposition) = 'EXPIRED' THEN 'EXPIRED'
            WHEN UPPER(e.disposition) = 'TRANSFER' THEN 'TRANSFER'
            ELSE 'OTHER'
        END AS disposition_group,
        CASE WHEN UPPER(e.disposition) = 'HOME' THEN 1 ELSE 0 END AS is_home_discharge,
        CASE WHEN UPPER(e.disposition) = 'ADMITTED' THEN 1 ELSE 0 END AS is_admitted_ed_disposition,
        CASE WHEN UPPER(e.disposition) = 'EXPIRED' THEN 1 ELSE 0 END AS is_expired_ed
    FROM `physionet-data.mimiciv_ed.edstays` e
),

ed_diagnoses AS (
    SELECT
        d.subject_id,
        d.stay_id,
        ARRAY_AGG(DISTINCT d.icd_code IGNORE NULLS) AS all_ed_icd_codes,
        ARRAY_AGG(DISTINCT d.icd_title IGNORE NULLS) AS all_ed_diagnosis_titles,
        COUNT(DISTINCT d.icd_code) AS num_ed_diagnoses,

        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%acute pancreatitis%' THEN 1 ELSE 0 END) AS acute_pancreatitis_flag,

        MAX(CASE
            WHEN REGEXP_CONTAINS(d.icd_code, r'^(S|T)')
              OR LOWER(d.icd_title) LIKE '%trauma%'
              OR LOWER(d.icd_title) LIKE '%injury%'
              OR LOWER(d.icd_title) LIKE '%fracture%'
              OR LOWER(d.icd_title) LIKE '%laceration%'
              OR LOWER(d.icd_title) LIKE '%contusion%'
              OR LOWER(d.icd_title) LIKE '%burn%'
            THEN 1 ELSE 0
        END) AS trauma_any_flag,

        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%fracture%' THEN 1 ELSE 0 END) AS fracture_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%dislocation%' THEN 1 ELSE 0 END) AS dislocation_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%sprain%' OR LOWER(d.icd_title) LIKE '%strain%' THEN 1 ELSE 0 END) AS sprain_strain_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%laceration%' THEN 1 ELSE 0 END) AS laceration_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%contusion%' THEN 1 ELSE 0 END) AS contusion_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%burn%' THEN 1 ELSE 0 END) AS burn_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%head injury%' OR LOWER(d.icd_title) LIKE '%intracranial%' OR LOWER(d.icd_title) LIKE '%concussion%' OR LOWER(d.icd_title) LIKE '%tbi%' THEN 1 ELSE 0 END) AS head_injury_tbi_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%abdominal pain%' THEN 1 ELSE 0 END) AS abdominal_pain_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%back pain%' THEN 1 ELSE 0 END) AS back_pain_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%chest pain%' THEN 1 ELSE 0 END) AS chest_pain_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%assault%' THEN 1 ELSE 0 END) AS assault_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%fall%' THEN 1 ELSE 0 END) AS fall_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%motor vehicle%' OR LOWER(d.icd_title) LIKE '%mvc%' OR LOWER(d.icd_title) LIKE '%traffic accident%' THEN 1 ELSE 0 END) AS mvc_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%gunshot%' OR LOWER(d.icd_title) LIKE '%stab%' OR LOWER(d.icd_title) LIKE '%penetrating%' THEN 1 ELSE 0 END) AS penetrating_injury_flag,
        MAX(CASE WHEN LOWER(d.icd_title) LIKE '%blunt%' THEN 1 ELSE 0 END) AS blunt_trauma_flag
    FROM `physionet-data.mimiciv_ed.diagnosis` d
    GROUP BY d.subject_id, d.stay_id
),

cohort_stays AS (
    SELECT
        eb.*,
        dx.all_ed_icd_codes,
        dx.all_ed_diagnosis_titles,
        dx.num_ed_diagnoses,
        COALESCE(dx.acute_pancreatitis_flag, 0) AS acute_pancreatitis_flag,
        COALESCE(dx.trauma_any_flag, 0) AS trauma_any_flag,
        COALESCE(dx.fracture_flag, 0) AS fracture_flag,
        COALESCE(dx.dislocation_flag, 0) AS dislocation_flag,
        COALESCE(dx.sprain_strain_flag, 0) AS sprain_strain_flag,
        COALESCE(dx.laceration_flag, 0) AS laceration_flag,
        COALESCE(dx.contusion_flag, 0) AS contusion_flag,
        COALESCE(dx.burn_flag, 0) AS burn_flag,
        COALESCE(dx.head_injury_tbi_flag, 0) AS head_injury_tbi_flag,
        COALESCE(dx.abdominal_pain_flag, 0) AS abdominal_pain_flag,
        COALESCE(dx.back_pain_flag, 0) AS back_pain_flag,
        COALESCE(dx.chest_pain_flag, 0) AS chest_pain_flag,
        COALESCE(dx.assault_flag, 0) AS assault_flag,
        COALESCE(dx.fall_flag, 0) AS fall_flag,
        COALESCE(dx.mvc_flag, 0) AS mvc_flag,
        COALESCE(dx.penetrating_injury_flag, 0) AS penetrating_injury_flag,
        COALESCE(dx.blunt_trauma_flag, 0) AS blunt_trauma_flag,
        CASE
            WHEN COALESCE(dx.acute_pancreatitis_flag, 0) = 1 THEN 'acute_pancreatitis'
            WHEN COALESCE(dx.trauma_any_flag, 0) = 1 THEN 'trauma'
            ELSE 'other'
        END AS diagnosis_type
    FROM ed_base eb
    INNER JOIN ed_diagnoses dx
        ON eb.subject_id = dx.subject_id
       AND eb.stay_id = dx.stay_id
    WHERE
        COALESCE(dx.acute_pancreatitis_flag, 0) = 1
        OR COALESCE(dx.trauma_any_flag, 0) = 1
),

patients AS (
    SELECT
        subject_id,
        anchor_age AS age,
        CASE
            WHEN anchor_age BETWEEN 18 AND 39 THEN '18-39'
            WHEN anchor_age BETWEEN 40 AND 64 THEN '40-64'
            WHEN anchor_age >= 65 THEN '65+'
            ELSE 'Unknown'
        END AS age_group
    FROM `physionet-data.mimiciv_3_1_hosp.patients`
),

admissions AS (
    SELECT
        hadm_id,
        subject_id,
        admission_type,
        admit_provider_id,
        admission_location,
        insurance AS insurance_raw,
        CASE
            WHEN insurance IS NULL THEN 'undocumented'
            WHEN LOWER(insurance) LIKE '%private%' THEN 'private'
            WHEN LOWER(insurance) LIKE '%medicare%' THEN 'Medicare'
            WHEN LOWER(insurance) LIKE '%medicaid%' THEN 'Medicaid'
            WHEN LOWER(insurance) LIKE '%self%' THEN 'uninsured'
            WHEN LOWER(insurance) LIKE '%uninsured%' THEN 'uninsured'
            ELSE 'undocumented'
        END AS insurance_group,
        language AS language_raw,
        CASE
            WHEN language IS NULL THEN 'undocumented'
            WHEN LOWER(language) LIKE '%english%' THEN 'English'
            ELSE 'non-English'
        END AS language_group,
        marital_status,
        hospital_expire_flag
    FROM `physionet-data.mimiciv_3_1_hosp.admissions`
),

triage AS (
    SELECT
        subject_id,
        stay_id,
        acuity AS triage_acuity,
        chiefcomplaint AS chiefcomplaint_raw,
        LOWER(TRIM(chiefcomplaint)) AS chiefcomplaint_clean,
        CASE
            WHEN LOWER(chiefcomplaint) LIKE '%abdominal%' OR LOWER(chiefcomplaint) LIKE '%abd pain%' THEN 'abdominal pain'
            WHEN LOWER(chiefcomplaint) LIKE '%trauma%' OR LOWER(chiefcomplaint) LIKE '%injury%' OR LOWER(chiefcomplaint) LIKE '%fall%' OR LOWER(chiefcomplaint) LIKE '%mvc%' OR LOWER(chiefcomplaint) LIKE '%assault%' THEN 'trauma'
            WHEN LOWER(chiefcomplaint) LIKE '%chest pain%' THEN 'chest pain'
            WHEN LOWER(chiefcomplaint) LIKE '%back pain%' THEN 'back pain'
            WHEN chiefcomplaint IS NULL THEN 'missing'
            ELSE 'other'
        END AS chiefcomplaint_group,
        temperature AS triage_temperature,
        heartrate AS triage_heartrate,
        resprate AS triage_resprate,
        o2sat AS triage_o2sat,
        sbp AS triage_sbp,
        dbp AS triage_dbp,
        pain AS triage_pain_raw
    FROM `physionet-data.mimiciv_ed.triage`
),

pain_events AS (
    SELECT
        v.subject_id,
        v.stay_id,
        v.charttime AS pain_charttime,
        v.pain AS pain_raw,
        CASE
            WHEN REGEXP_CONTAINS(TRIM(CAST(v.pain AS STRING)), r'^[0-9]+(\.[0-9]+)?$')
                AND SAFE_CAST(TRIM(CAST(v.pain AS STRING)) AS FLOAT64) BETWEEN 0 AND 10
                THEN SAFE_CAST(TRIM(CAST(v.pain AS STRING)) AS FLOAT64)
            WHEN REGEXP_CONTAINS(TRIM(CAST(v.pain AS STRING)), r'^[0-9]+/[0-9]+$')
                THEN SAFE_CAST(REGEXP_EXTRACT(TRIM(CAST(v.pain AS STRING)), r'^([0-9]+)') AS FLOAT64)
            ELSE NULL
        END AS pain_numeric,
        CASE
            WHEN v.pain IS NULL THEN 'missing'
            WHEN REGEXP_CONTAINS(TRIM(CAST(v.pain AS STRING)), r'^[0-9]+(\.[0-9]+)?$')
                AND SAFE_CAST(TRIM(CAST(v.pain AS STRING)) AS FLOAT64) BETWEEN 0 AND 10
                THEN NULL
            WHEN REGEXP_CONTAINS(LOWER(TRIM(CAST(v.pain AS STRING))), r'unable|uta|uto|nonverbal|non verbal|sedated|asleep') THEN 'unable_to_assess'
            WHEN REGEXP_CONTAINS(LOWER(TRIM(CAST(v.pain AS STRING))), r'refused|declined') THEN 'refused'
            WHEN REGEXP_CONTAINS(LOWER(TRIM(CAST(v.pain AS STRING))), r'none|no pain') THEN 'text_none'
            WHEN REGEXP_CONTAINS(TRIM(CAST(v.pain AS STRING)), r'^[0-9]+/[0-9]+$') THEN 'fraction_or_score_text'
            WHEN REGEXP_CONTAINS(TRIM(CAST(v.pain AS STRING)), r'[0-9]+\s*-\s*[0-9]+') THEN 'range'
            ELSE 'other_text'
        END AS pain_non_numeric_reason,
        v.temperature,
        v.heartrate,
        v.resprate,
        v.o2sat,
        v.sbp,
        v.dbp
    FROM `physionet-data.mimiciv_ed.vitalsign` v
    INNER JOIN cohort_stays cs
        ON v.subject_id = cs.subject_id
       AND v.stay_id = cs.stay_id
    WHERE v.pain IS NOT NULL
),

initial_pain AS (
    SELECT
        subject_id,
        stay_id,
        pain_charttime AS initial_pain_time,
        pain_numeric AS initial_pain_score,
        TIMESTAMP_TRUNC(TIMESTAMP(pain_charttime), HOUR) AS initial_pain_hour
    FROM (
        SELECT
            pe.*,
            ROW_NUMBER() OVER (
                PARTITION BY subject_id, stay_id
                ORDER BY pain_charttime
            ) AS rn
        FROM pain_events pe
        WHERE pain_numeric IS NOT NULL
    )
    WHERE rn = 1
),

hospital_diagnoses AS (
    SELECT
        di.subject_id,
        di.hadm_id,
        ARRAY_AGG(DISTINCT di.icd_code IGNORE NULLS) AS all_hosp_icd_codes,
        ARRAY_AGG(DISTINCT dd.long_title IGNORE NULLS) AS all_hosp_diagnosis_titles,

        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'copd|asthma|pulmonary|lung disease|emphysema|chronic bronchitis') THEN 1 ELSE 0 END) AS lung_disease_flag,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'coronary|heart failure|myocardial|arrhythmia|cardiac|cardiomyopathy') THEN 1 ELSE 0 END) AS cardiac_disease_flag,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'hypertension|hypertensive') THEN 1 ELSE 0 END) AS hypertension_flag,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'diabetes|diabetic') THEN 1 ELSE 0 END) AS diabetes_flag,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'renal|kidney|ckd|esrd') THEN 1 ELSE 0 END) AS renal_disease_flag,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'obesity|obese') THEN 1 ELSE 0 END) AS obesity_flag,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'cancer|malignant|malignancy|neoplasm|lymphoma|leukemia|metastatic') THEN 1 ELSE 0 END) AS cancer_flag,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(dd.long_title), r'tobacco|smoking|nicotine') THEN 1 ELSE 0 END) AS smoking_flag

    FROM `physionet-data.mimiciv_3_1_hosp.diagnoses_icd` di
    LEFT JOIN `physionet-data.mimiciv_3_1_hosp.d_icd_diagnoses` dd
        ON di.icd_code = dd.icd_code
       AND di.icd_version = dd.icd_version
    INNER JOIN cohort_stays cs
        ON di.subject_id = cs.subject_id
       AND di.hadm_id = cs.hadm_id
    GROUP BY di.subject_id, di.hadm_id
),

analgesic_pyxis AS (
    SELECT
        p.subject_id,
        p.stay_id,
        ARRAY_AGG(
            STRUCT(
                p.charttime AS charttime,
                p.name AS medication_name,
                CASE
                    WHEN REGEXP_CONTAINS(LOWER(p.name), r'morphine|hydromorphone|dilaudid|fentanyl|oxycodone|hydrocodone|codeine|tramadol|methadone') THEN 'opioid'
                    WHEN REGEXP_CONTAINS(LOWER(p.name), r'ibuprofen|ketorolac|toradol|naproxen|diclofenac|celecoxib|nsaid') THEN 'NSAID'
                    WHEN REGEXP_CONTAINS(LOWER(p.name), r'acetaminophen|tylenol|paracetamol') THEN 'acetaminophen'
                    WHEN REGEXP_CONTAINS(LOWER(p.name), r'ketamine') THEN 'ketamine'
                    WHEN REGEXP_CONTAINS(LOWER(p.name), r'lidocaine|bupivacaine|ropivacaine|benzocaine') THEN 'local_anesthetic'
                    ELSE 'other_analgesic'
                END AS analgesic_class
            )
            ORDER BY p.charttime
        ) AS analgesic_events,

        COUNT(*) AS num_analgesic_events,
        MIN(p.charttime) AS first_analgesic_time,

        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(p.name), r'morphine|hydromorphone|dilaudid|fentanyl|oxycodone|hydrocodone|codeine|tramadol|methadone') THEN 1 ELSE 0 END) AS opioid_given,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(p.name), r'ibuprofen|ketorolac|toradol|naproxen|diclofenac|celecoxib|nsaid') THEN 1 ELSE 0 END) AS nsaid_given,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(p.name), r'acetaminophen|tylenol|paracetamol') THEN 1 ELSE 0 END) AS acetaminophen_given,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(p.name), r'ketamine') THEN 1 ELSE 0 END) AS ketamine_given,
        MAX(CASE WHEN REGEXP_CONTAINS(LOWER(p.name), r'lidocaine|bupivacaine|ropivacaine|benzocaine') THEN 1 ELSE 0 END) AS local_anesthetic_given

    FROM `physionet-data.mimiciv_ed.pyxis` p
    INNER JOIN cohort_stays cs
        ON p.subject_id = cs.subject_id
       AND p.stay_id = cs.stay_id
    WHERE REGEXP_CONTAINS(
        LOWER(p.name),
        r'morphine|hydromorphone|dilaudid|fentanyl|oxycodone|hydrocodone|codeine|tramadol|methadone|ibuprofen|ketorolac|toradol|naproxen|diclofenac|celecoxib|nsaid|acetaminophen|tylenol|paracetamol|ketamine|lidocaine|bupivacaine|ropivacaine|benzocaine'
    )
    GROUP BY p.subject_id, p.stay_id
),

icu_features AS (
    SELECT
        icu.subject_id,
        icu.hadm_id,
        1 AS icu_admitted,
        MIN(icu.intime) AS first_icu_intime
    FROM `physionet-data.mimiciv_3_1_icu.icustays` icu
    INNER JOIN cohort_stays cs
        ON icu.subject_id = cs.subject_id
       AND icu.hadm_id = cs.hadm_id
    GROUP BY icu.subject_id, icu.hadm_id
),

hour_bounds AS (
    SELECT
        TIMESTAMP_TRUNC(MIN(TIMESTAMP(intime)), HOUR) AS min_hour,
        TIMESTAMP_TRUNC(MAX(TIMESTAMP(outtime)), HOUR) AS max_hour
    FROM ed_base
),

all_hours AS (
    SELECT hour_ts
    FROM hour_bounds,
    UNNEST(GENERATE_TIMESTAMP_ARRAY(min_hour, max_hour, INTERVAL 1 HOUR)) AS hour_ts
),

arrival_hourly AS (
    SELECT
        TIMESTAMP_TRUNC(TIMESTAMP(intime), HOUR) AS hour_ts,
        COUNT(*) AS arrivals_this_hour
    FROM ed_base
    GROUP BY hour_ts
),

departure_hourly AS (
    SELECT
        TIMESTAMP_TRUNC(TIMESTAMP(outtime), HOUR) AS hour_ts,
        COUNT(*) AS departures_this_hour
    FROM ed_base
    WHERE outtime IS NOT NULL
    GROUP BY hour_ts
),

ed_hourly_flow AS (
    SELECT
        h.hour_ts,
        COALESCE(a.arrivals_this_hour, 0) AS arrivals_this_hour,
        COALESCE(d.departures_this_hour, 0) AS departures_this_hour
    FROM all_hours h
    LEFT JOIN arrival_hourly a
        ON h.hour_ts = a.hour_ts
    LEFT JOIN departure_hourly d
        ON h.hour_ts = d.hour_ts
),

ed_hourly_metrics AS (
    SELECT
        hour_ts,

        /*
        Approximate ED census at the start of the hour.
        This avoids the expensive pain-time-by-stay interval join.
        */
        SUM(arrivals_this_hour - departures_this_hour) OVER (
            ORDER BY hour_ts
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ) AS ed_census_at_hour_start,

        arrivals_this_hour,

        SUM(arrivals_this_hour) OVER (
            ORDER BY hour_ts
            ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
        ) AS ed_arrivals_past_1hr,

        SUM(arrivals_this_hour) OVER (
            ORDER BY hour_ts
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS ed_arrivals_past_4hr

    FROM ed_hourly_flow
),

workflow_initial_pain AS (
    SELECT
        ip.subject_id,
        ip.stay_id,
        COALESCE(ehm.ed_census_at_hour_start, 0) AS ed_census_at_pain,
        COALESCE(ehm.ed_arrivals_past_1hr, 0) AS ed_arrivals_past_1hr,
        COALESCE(ehm.ed_arrivals_past_4hr, 0) AS ed_arrivals_past_4hr
    FROM initial_pain ip
    LEFT JOIN ed_hourly_metrics ehm
        ON ip.initial_pain_hour = ehm.hour_ts
)

SELECT
    cs.subject_id,
    cs.stay_id,
    cs.hadm_id,

    cs.intime,
    cs.outtime,
    cs.ed_los_minutes,

    cs.sex,
    cs.race_raw,
    cs.race_ethnicity,
    pa.age,
    pa.age_group,

    adm.admission_type,
    adm.admit_provider_id AS provider_id,
    adm.admission_location,
    adm.insurance_raw,
    adm.insurance_group,
    adm.language_raw,
    adm.language_group,
    adm.marital_status,
    adm.hospital_expire_flag,

    cs.arrival_transport,
    cs.disposition,
    cs.disposition_group,
    cs.is_home_discharge,
    cs.is_admitted_ed_disposition,
    cs.is_expired_ed,

    CASE WHEN cs.hadm_id IS NOT NULL THEN 1 ELSE 0 END AS has_hadm_id,
    CASE WHEN adm.hadm_id IS NOT NULL THEN 1 ELSE 0 END AS confirmed_hospital_admission,

    COALESCE(icu.icu_admitted, 0) AS icu_admitted,
    icu.first_icu_intime,
    DATETIME_DIFF(icu.first_icu_intime, cs.intime, MINUTE) AS minutes_ed_arrival_to_icu,

    EXTRACT(YEAR FROM cs.intime) AS year,
    CASE
        WHEN EXTRACT(YEAR FROM cs.intime) BETWEEN 2011 AND 2013 THEN '2011-2013'
        WHEN EXTRACT(YEAR FROM cs.intime) BETWEEN 2014 AND 2016 THEN '2014-2016'
        WHEN EXTRACT(YEAR FROM cs.intime) BETWEEN 2017 AND 2019 THEN '2017-2019'
        WHEN EXTRACT(YEAR FROM cs.intime) BETWEEN 2020 AND 2022 THEN '2020-2022'
        ELSE 'other'
    END AS era,
    EXTRACT(HOUR FROM cs.intime) AS arrival_hour,
    FORMAT_DATE('%A', DATE(cs.intime)) AS arrival_day_of_week,
    CASE WHEN EXTRACT(DAYOFWEEK FROM cs.intime) IN (1, 7) THEN 1 ELSE 0 END AS arrival_weekend,
    CASE
        WHEN EXTRACT(HOUR FROM cs.intime) BETWEEN 7 AND 14 THEN 'day'
        WHEN EXTRACT(HOUR FROM cs.intime) BETWEEN 15 AND 22 THEN 'evening'
        ELSE 'night'
    END AS arrival_shift,

    tr.triage_acuity,
    tr.chiefcomplaint_raw,
    tr.chiefcomplaint_clean,
    tr.chiefcomplaint_group,
    tr.triage_temperature,
    tr.triage_heartrate,
    tr.triage_resprate,
    tr.triage_o2sat,
    tr.triage_sbp,
    tr.triage_dbp,
    tr.triage_pain_raw,

    pe.pain_charttime,
    pe.pain_raw,
    pe.pain_numeric,
    pe.pain_non_numeric_reason,
    pe.temperature,
    pe.heartrate,
    pe.resprate,
    pe.o2sat,
    pe.sbp,
    pe.dbp,
    DATETIME_DIFF(pe.pain_charttime, cs.intime, MINUTE) AS minutes_since_ed_arrival_to_pain,

    ip.initial_pain_time,
    ip.initial_pain_score,

    cs.all_ed_icd_codes,
    cs.all_ed_diagnosis_titles,
    cs.num_ed_diagnoses,
    cs.acute_pancreatitis_flag,
    cs.trauma_any_flag,
    cs.diagnosis_type,
    cs.fracture_flag,
    cs.dislocation_flag,
    cs.sprain_strain_flag,
    cs.laceration_flag,
    cs.contusion_flag,
    cs.burn_flag,
    cs.head_injury_tbi_flag,
    cs.abdominal_pain_flag,
    cs.back_pain_flag,
    cs.chest_pain_flag,
    cs.assault_flag,
    cs.fall_flag,
    cs.mvc_flag,
    cs.penetrating_injury_flag,
    cs.blunt_trauma_flag,

    hd.all_hosp_icd_codes,
    hd.all_hosp_diagnosis_titles,
    COALESCE(hd.lung_disease_flag, 0) AS lung_disease_flag,
    COALESCE(hd.cardiac_disease_flag, 0) AS cardiac_disease_flag,
    COALESCE(hd.hypertension_flag, 0) AS hypertension_flag,
    COALESCE(hd.diabetes_flag, 0) AS diabetes_flag,
    COALESCE(hd.renal_disease_flag, 0) AS renal_disease_flag,
    COALESCE(hd.obesity_flag, 0) AS obesity_flag,
    COALESCE(hd.cancer_flag, 0) AS cancer_flag,
    COALESCE(hd.smoking_flag, 0) AS smoking_flag,

    COALESCE(ap.num_analgesic_events, 0) AS num_analgesic_events,
    CASE WHEN ap.num_analgesic_events IS NOT NULL THEN 1 ELSE 0 END AS any_analgesic_given,
    ap.first_analgesic_time,
    ap.analgesic_events,
    COALESCE(ap.opioid_given, 0) AS opioid_given,
    COALESCE(ap.nsaid_given, 0) AS nsaid_given,
    COALESCE(ap.acetaminophen_given, 0) AS acetaminophen_given,
    COALESCE(ap.ketamine_given, 0) AS ketamine_given,
    COALESCE(ap.local_anesthetic_given, 0) AS local_anesthetic_given,

    wf.ed_census_at_pain,
    wf.ed_arrivals_past_1hr,
    wf.ed_arrivals_past_4hr

FROM cohort_stays cs
LEFT JOIN patients pa
    ON cs.subject_id = pa.subject_id
LEFT JOIN admissions adm
    ON cs.hadm_id = adm.hadm_id
LEFT JOIN triage tr
    ON cs.subject_id = tr.subject_id
   AND cs.stay_id = tr.stay_id
LEFT JOIN pain_events pe
    ON cs.subject_id = pe.subject_id
   AND cs.stay_id = pe.stay_id
LEFT JOIN initial_pain ip
    ON cs.subject_id = ip.subject_id
   AND cs.stay_id = ip.stay_id
LEFT JOIN hospital_diagnoses hd
    ON cs.subject_id = hd.subject_id
   AND cs.hadm_id = hd.hadm_id
LEFT JOIN analgesic_pyxis ap
    ON cs.subject_id = ap.subject_id
   AND cs.stay_id = ap.stay_id
LEFT JOIN icu_features icu
    ON cs.subject_id = icu.subject_id
   AND cs.hadm_id = icu.hadm_id
LEFT JOIN workflow_initial_pain wf
    ON cs.subject_id = wf.subject_id
   AND cs.stay_id = wf.stay_id

WHERE pe.pain_raw IS NOT NULL

ORDER BY
    cs.subject_id,
    cs.stay_id,
    pe.pain_charttime;