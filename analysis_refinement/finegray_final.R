#!/usr/bin/env Rscript
# Fine-Gray competing-risk model on the S6 primary cohort.
# Event of interest: first pain reassessment (fg_status = 1).
# Competing event:   structural departure without reassessment -- eloped,
#                    LWBS, AMA, expired, transfer (fg_status = 2).
# Censored:          all other departures without reassessment (fg_status = 0).
#
# Uses survival::finegray() + weighted coxph() (scales to 42k rows, unlike
# cmprsk::crr). CIF curves by insurance via cmprsk::cuminc.
# Run: Rscript analysis_refinement/finegray_final.R

suppressPackageStartupMessages({
  library(survival)
  library(cmprsk)
})

root <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=",
  commandArgs(trailingOnly = FALSE), value = TRUE))), ".."))
out_dir <- file.path(root, "analysis_refinement", "outputs", "final")
fig_dir <- file.path(root, "analysis_refinement", "figures")

d <- read.csv(file.path(out_dir, "finegray_input.csv"), stringsAsFactors = FALSE)
cat(sprintf("n=%d | reassessed=%d structural=%d censored=%d\n",
            nrow(d), sum(d$fg_status == 1), sum(d$fg_status == 2),
            sum(d$fg_status == 0)))

d$race_ethnicity  <- relevel(factor(d$race_ethnicity), ref = "White")
d$insurance_group <- relevel(factor(d$insurance_group), ref = "private")
d$language_group  <- relevel(factor(d$language_group), ref = "English")
d$sex             <- relevel(factor(d$sex), ref = "F")
d$age_group       <- relevel(factor(d$age_group), ref = "40-64")
d$injury_group    <- relevel(factor(d$injury_group), ref = "acute_pancreatitis")
d$arrival_mode    <- relevel(factor(d$arrival_mode), ref = "walk_in")
d$arrival_shift   <- relevel(factor(d$arrival_shift), ref = "day")
d$year_era        <- factor(d$year_era)
d$fg_status       <- factor(d$fg_status, levels = c(0, 1, 2),
                            labels = c("censored", "reassessed", "structural_departure"))

fg <- finegray(Surv(duration_minutes, fg_status) ~ ., data = d,
               etype = "reassessed")
fit <- coxph(Surv(fgstart, fgstop, fgstatus) ~ initial_pain_score + injury_group +
               race_ethnicity + age_group + sex + insurance_group + language_group +
               triage_acuity + heartrate_0_z + resprate_0_z + sbp_0_z +
               arrival_mode + arrival_shift + arrival_weekend +
               ed_arrivals_past_1hr + ed_census_at_initial_pain_hour + year_era,
             weight = fgwt, data = fg)

s <- summary(fit)
res <- data.frame(
  term    = rownames(s$coefficients),
  coef    = s$coefficients[, "coef"],
  sHR     = round(s$coefficients[, "exp(coef)"], 3),
  ci_low  = round(s$conf.int[, "lower .95"], 3),
  ci_high = round(s$conf.int[, "upper .95"], 3),
  se      = s$coefficients[, "robust se"],
  z       = s$coefficients[, "z"],
  p       = ifelse(s$coefficients[, "Pr(>|z|)"] < 0.001, "<0.001",
                   round(s$coefficients[, "Pr(>|z|)"], 3)),
  row.names = NULL
)
write.csv(res, file.path(out_dir, "finegray_shr.csv"), row.names = FALSE)
cat("\nKey sHRs:\n")
print(res[grepl("race_ethnicity|insurance_group|language_group", res$term),
          c("term", "sHR", "ci_low", "ci_high", "p")], row.names = FALSE)

# --- CIF curves by insurance (unadjusted, for the absolute-scale figure) ---
ci <- cuminc(ftime = d$duration_minutes, fstatus = as.integer(d$fg_status) - 1,
             group = d$insurance_group, cencode = 0)
keep <- grep(" 1$", names(ci), value = TRUE)  # event 1 = reassessment
cif_rows <- do.call(rbind, lapply(keep, function(k) {
  data.frame(group = sub(" 1$", "", k), time = ci[[k]]$time, est = ci[[k]]$est)
}))
write.csv(cif_rows, file.path(out_dir, "finegray_cif_curves.csv"), row.names = FALSE)
cat(sprintf("\nWrote %s and %s\n",
            file.path(out_dir, "finegray_shr.csv"),
            file.path(out_dir, "finegray_cif_curves.csv")))
