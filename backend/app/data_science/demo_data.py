"""A small, clearly-labelled demo dataset (master spec §55).

Employee attrition — deliberately seeded with missing values, duplicate rows,
inconsistent category labels, numeric-as-string, and salary outliers so every
part of the workspace has something to show.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEMO_NAME = "Demo — Employee Attrition"
DEMO_TARGET = "Attrition"


def build_demo_dataframe(n: int = 600, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    departments = rng.choice(
        ["Sales", "sales", "Engineering", "engineering ", "Support", "SUPPORT", "Marketing"],
        size=n,
        p=[0.2, 0.05, 0.3, 0.05, 0.2, 0.05, 0.15],
    )
    genders = rng.choice(["Male", "male", "M", "Female", "female", "F"], size=n, p=[0.28, 0.08, 0.04, 0.4, 0.15, 0.05])
    contract = rng.choice(["Full-time", "Part-time", "Contract"], size=n, p=[0.7, 0.18, 0.12])

    age = rng.normal(38, 9, n).clip(20, 64).round().astype(float)
    tenure_years = rng.gamma(2.0, 2.2, n).clip(0, 30).round(1)
    monthly_hours = rng.normal(170, 22, n).clip(90, 310).round().astype(float)
    satisfaction = rng.beta(2.5, 2.0, n).round(3)

    base_salary = 30000 + age * 900 + tenure_years * 1500 + (contract == "Full-time") * 8000
    salary = (base_salary + rng.normal(0, 6000, n)).clip(18000, None).round(0)
    # Inject extreme high-salary outliers.
    outlier_idx = rng.choice(n, size=max(3, n // 120), replace=False)
    salary[outlier_idx] = salary[outlier_idx] * rng.uniform(4, 7, size=len(outlier_idx))

    # Attrition driven by satisfaction, contract, tenure (+ noise).
    logit = (
        -1.1
        - 3.0 * (satisfaction - 0.5)
        + 0.9 * (contract == "Contract")
        + 0.5 * (contract == "Part-time")
        - 0.06 * tenure_years
        + 0.015 * (monthly_hours - 170)
    )
    prob = 1 / (1 + np.exp(-logit))
    attrition = np.where(rng.random(n) < prob, "Yes", "No")

    df = pd.DataFrame(
        {
            "EmployeeID": [f"E{1000 + i}" for i in range(n)],
            "Age": age,
            "Department": departments,
            "Gender": genders,
            "ContractType": contract,
            "TenureYears": tenure_years,
            "MonthlyHours": monthly_hours,
            "Satisfaction": satisfaction,
            # Salary stored as a string with thousands separators, on purpose.
            "MonthlySalary": [f"{v:,.0f}" for v in salary],
            "Attrition": attrition,
        }
    )

    # Missing values.
    for col, frac in (("Age", 0.06), ("Satisfaction", 0.09), ("Department", 0.03)):
        idx = rng.choice(n, size=int(n * frac), replace=False)
        df.loc[idx, col] = np.nan

    # Duplicate rows.
    dup = df.sample(max(5, n // 60), random_state=seed)
    df = pd.concat([df, dup], ignore_index=True)

    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


__all__ = ["build_demo_dataframe", "DEMO_NAME", "DEMO_TARGET"]
