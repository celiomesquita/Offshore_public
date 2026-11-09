"""Negative Binomial panel regression for removal demand (Results Table R-3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

DEFAULT_PANEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "analysis_outputs"
    / "public"
    / "panel_aircraft_ata_month.csv"
)
MONTH_REFERENCE = "2024-01"


@dataclass(frozen=True)
class NBModelSummary:
    """Diagnostics and metadata for the fitted NB panel model."""

    n_obs: int
    n_aircraft: int
    n_ata2: int
    n_months: int
    poisson_pearson_ratio: float
    nb_alpha: float
    nb_pearson_ratio: float
    log_likelihood: float
    excluded_low_exposure: bool
    excluded_zero_hour_rows: int


@dataclass(frozen=True)
class NBEstimate:
    """One incidence rate ratio row for publication."""

    model: str
    variable: str
    irr: float
    ci_lower: float
    ci_upper: float
    p_value: float


def load_panel(path: Path | None = None) -> pd.DataFrame:
    """Load the anonymised aircraft × ATA × month panel."""
    return pd.read_csv(path or DEFAULT_PANEL_PATH)


def prepare_nb_panel(
    panel: pd.DataFrame,
    *,
    exclude_low_exposure: bool = True,
    require_positive_hours: bool = True,
) -> pd.DataFrame:
    """Prepare the estimation sample with utilisation covariates and exposure offset."""
    frame = panel.copy()
    if exclude_low_exposure:
        frame = frame.loc[~frame["low_exposure"]]
    if require_positive_hours:
        frame = frame.loc[frame["H_im"] > 0]

    frame["takeoffs_per_hour"] = frame["takeoffs_im"] / frame["H_im"]
    frame["starts_per_hour"] = frame["starts_im"] / frame["H_im"]
    frame["log_exposure"] = np.log(frame["H_im"])
    frame["month"] = pd.Categorical(frame["month"], ordered=True)
    return frame.reset_index(drop=True)


def _fixed_effects_terms(reference_month: str = MONTH_REFERENCE) -> str:
    return (
        f'C(pt_id) + C(ata2) + C(month, Treatment(reference="{reference_month}"))'
    )


def estimate_nb_alpha(poisson_result: sm.regression.linear_model.RegressionResultsWrapper) -> float:
    """Method-of-moments NB dispersion from Poisson overdispersion."""
    pearson_ratio = float(poisson_result.pearson_chi2 / poisson_result.df_resid)
    mean_y = float(poisson_result.model.endog.mean())
    return max((pearson_ratio - 1.0) / mean_y, 0.01)


def _fit_poisson(df: pd.DataFrame, formula_covariates: str, reference_month: str) -> object:
    formula = f"Y_iam ~ {formula_covariates} + {_fixed_effects_terms(reference_month)}"
    return smf.glm(
        formula,
        data=df,
        family=sm.families.Poisson(),
        offset=df["log_exposure"],
    ).fit(maxiter=200)


def _fit_nb(df: pd.DataFrame, formula_covariates: str, alpha: float, reference_month: str) -> object:
    formula = f"Y_iam ~ {formula_covariates} + {_fixed_effects_terms(reference_month)}"
    return smf.glm(
        formula,
        data=df,
        family=sm.families.NegativeBinomial(alpha=alpha),
        offset=df["log_exposure"],
    ).fit(maxiter=300)


def _extract_estimate(model_name: str, variable: str, result: object) -> NBEstimate:
    ci = result.conf_int().loc[variable]
    return NBEstimate(
        model=model_name,
        variable=variable,
        irr=float(np.exp(result.params[variable])),
        ci_lower=float(np.exp(ci[0])),
        ci_upper=float(np.exp(ci[1])),
        p_value=float(result.pvalues[variable]),
    )


def panel_nb_alpha(root: Path | None = None) -> float:
    """Return the NB dispersion estimate from the panel demand model (Table R-3)."""
    base = root or Path(__file__).resolve().parent.parent
    panel = load_panel(base / "analysis_outputs" / "public" / "panel_aircraft_ata_month.csv")
    _, summary, _, _ = fit_nb_panel_models(panel)
    return summary.nb_alpha


def fit_nb_panel_models(
    panel: pd.DataFrame,
    *,
    reference_month: str = MONTH_REFERENCE,
) -> tuple[list[NBEstimate], NBModelSummary, object, object]:
    """Fit Poisson baseline and NB panel models; return IRR table rows and diagnostics."""
    df = prepare_nb_panel(panel)

    poisson_joint = _fit_poisson(df, "takeoffs_per_hour + starts_per_hour", reference_month)
    alpha = estimate_nb_alpha(poisson_joint)
    nb_joint = _fit_nb(df, "takeoffs_per_hour + starts_per_hour", alpha, reference_month)

    estimates = [
        _extract_estimate("Joint", "takeoffs_per_hour", nb_joint),
        _extract_estimate("Joint", "starts_per_hour", nb_joint),
        _extract_estimate("Takeoffs only", "takeoffs_per_hour", _fit_nb(df, "takeoffs_per_hour", alpha, reference_month)),
        _extract_estimate("Starts only", "starts_per_hour", _fit_nb(df, "starts_per_hour", alpha, reference_month)),
    ]

    summary = NBModelSummary(
        n_obs=len(df),
        n_aircraft=int(df["pt_id"].nunique()),
        n_ata2=int(df["ata2"].nunique()),
        n_months=int(df["month"].nunique()),
        poisson_pearson_ratio=float(poisson_joint.pearson_chi2 / poisson_joint.df_resid),
        nb_alpha=float(alpha),
        nb_pearson_ratio=float(nb_joint.pearson_chi2 / nb_joint.df_resid),
        log_likelihood=float(nb_joint.llf),
        excluded_low_exposure=True,
        excluded_zero_hour_rows=int((~panel["low_exposure"] & (panel["H_im"] == 0)).sum()),
    )
    return estimates, summary, poisson_joint, nb_joint


def estimates_to_frame(estimates: list[NBEstimate]) -> pd.DataFrame:
    """Convert estimate rows to a publication-ready DataFrame."""
    return pd.DataFrame([estimate.__dict__ for estimate in estimates])


def month_seasonality_frame(nb_joint_result: object) -> pd.DataFrame:
    """Extract month fixed-effect IRRs relative to the reference month."""
    rows: list[dict[str, float | str]] = [
        {
            "month": MONTH_REFERENCE,
            "irr": 1.0,
            "ci_lower": 1.0,
            "ci_upper": 1.0,
        }
    ]
    prefix = 'C(month, Treatment(reference="2024-01"))[T.'
    for param_name in nb_joint_result.params.index:
        if not param_name.startswith(prefix):
            continue
        month = param_name[len(prefix) :].rstrip("]")
        ci = nb_joint_result.conf_int().loc[param_name]
        rows.append(
            {
                "month": month,
                "irr": float(np.exp(nb_joint_result.params[param_name])),
                "ci_lower": float(np.exp(ci[0])),
                "ci_upper": float(np.exp(ci[1])),
            }
        )
    frame = pd.DataFrame(rows).sort_values("month").reset_index(drop=True)
    return frame


def write_r3_latex(
    estimates: pd.DataFrame,
    summary: NBModelSummary,
    output_path: Path,
) -> None:
    """Write Results Table R-3 as a LaTeX fragment."""
    label_map = {
        "takeoffs_per_hour": "Takeoffs/FH",
        "starts_per_hour": "Starts/FH",
    }
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Negative Binomial panel model incidence rate ratios for unscheduled removal demand (R-3).}",
        "\\label{tab:r3-nb-panel}",
        "\\small",
        "\\setlength{\\tabcolsep}{4pt}",
        "\\makebox[\\linewidth][c]{%",
        "\\begin{tabular*}{1.04\\linewidth}{@{\\extracolsep{\\fill}}llrrr@{}}",
        "\\toprule",
        "Specification & Covariate & IRR & 95\\% CI & $p$ \\\\",
        "\\midrule",
    ]
    for row in estimates.itertuples(index=False):
        p_text = f"{row.p_value:.3f}" if row.p_value >= 0.001 else f"{row.p_value:.2e}"
        lines.append(
            f"{row.model} & {label_map[row.variable]} & {row.irr:.2f} & "
            f"[{row.ci_lower:.2f}, {row.ci_upper:.2f}] & {p_text} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular*}%",
            "}",
            "\\par\\smallskip",
            "{\\footnotesize \\textit{Note:} Dependent variable: unscheduled removal count $Y_{iam}$. "
            f"Sample: {summary.n_obs:,} aircraft--ATA--month cells ({summary.n_aircraft} aircraft, "
            f"{summary.n_ata2} ATA chapters, {summary.n_months} months) with positive flight-hour exposure; "
            "PT-022--PT-024 excluded. All models include aircraft, ATA, and month fixed effects with "
            f"$\\log(H_{{im}})$ offset. Poisson baseline Pearson $\\chi^2/df = {summary.poisson_pearson_ratio:.2f}$; "
            f"NB dispersion $\\alpha = {summary.nb_alpha:.2f}$ "
            f"(NB Pearson $\\chi^2/df = {summary.nb_pearson_ratio:.2f}$). "
            "Takeoffs-only and starts-only rows are sensitivity specifications.}",
            "\\end{table}",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_seasonality_figure(seasonality: pd.DataFrame, output_path: Path) -> None:
    """Write month fixed-effect IRR plot (Figure R-S)."""
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    x = np.arange(len(seasonality))
    ax.errorbar(
        x,
        seasonality["irr"],
        yerr=[
            seasonality["irr"] - seasonality["ci_lower"],
            seasonality["ci_upper"] - seasonality["irr"],
        ],
        fmt="o-",
        color="#4C72B0",
        ecolor="#888888",
        capsize=3,
        linewidth=1.5,
        markersize=5,
    )
    ax.axhline(1.0, color="#C44E52", linestyle="--", linewidth=1.0, label="Reference month (2024-01)")
    ax.set_xticks(x)
    ax.set_xticklabels(seasonality["month"], rotation=45, ha="right")
    ax.set_ylabel("Removal rate ratio vs 2024-01")
    ax.set_xlabel("Calendar month")
    ax.set_title("Monthly fixed effects from the NB panel model")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def export_nb_panel_results(
    root: Path | None = None,
    *,
    panel_path: Path | None = None,
    table_tex: Path | None = None,
    csv_path: Path | None = None,
    seasonality_figure: Path | None = None,
    seasonality_csv: Path | None = None,
) -> tuple[pd.DataFrame, NBModelSummary, pd.DataFrame]:
    """Export Table R-3, seasonality figure, and CSV summaries."""
    base = root or Path(__file__).resolve().parent.parent
    panel = load_panel(panel_path or base / "analysis_outputs" / "public" / "panel_aircraft_ata_month.csv")
    estimates, summary, _poisson, nb_joint = fit_nb_panel_models(panel)
    estimate_frame = estimates_to_frame(estimates)
    seasonality = month_seasonality_frame(nb_joint)

    if csv_path is None:
        csv_path = base / "analysis_outputs" / "public" / "table_r3_nb_panel.csv"
    if table_tex is None:
        table_tex = base / "latex" / "manuscript" / "tables" / "table_r3_nb_panel.tex"
    if seasonality_figure is None:
        seasonality_figure = base / "latex" / "manuscript" / "figures" / "fig_r_seasonality.pdf"
    if seasonality_csv is None:
        seasonality_csv = base / "analysis_outputs" / "public" / "table_r3_month_effects.csv"

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    estimate_frame.to_csv(csv_path, index=False)
    seasonality.to_csv(seasonality_csv, index=False)
    write_r3_latex(estimate_frame, summary, table_tex)
    write_seasonality_figure(seasonality, seasonality_figure)
    return estimate_frame, summary, seasonality
