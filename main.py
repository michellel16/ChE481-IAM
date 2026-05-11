"""
Simplified RICE/DICE IAM — runner and visualiser

Produces four figures:
  Fig 1 — Global CO₂ emissions under all 5 SSP scenarios
  Fig 2 — Global + top-N regional emissions for a chosen scenario (SSP2)
  Fig 3 — Global mean temperature rise by SSP
  Fig 4 — Regional emissions heatmap at a target year (2100)
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "backend"))
from iam_model import run_iam, SSP_CONFIGS, REGIONS, N_REGIONS

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

START_YEAR   = 2015
END_YEAR     = 2100
REGIONAL_SSP = "SSP2"   # which SSP to use for the regional breakdown plot
TOP_N        = 6        # how many regions to show in the regional panel
HEATMAP_YEAR = 2100     # target year for the heatmap

# FIGURE 1: Global emissions — all SSPs
def plot_global_emissions(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))

    for ssp_key, res in results.items():
        ax.plot(res["years"], res["global_emissions"],
                color=res["ssp_color"], linewidth=2.2,
                label=res["ssp_name"])

    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("GtCO₂ / year", fontsize=12)
    ax.set_title("Global CO₂ Emissions by SSP Scenario\n"
                 "(Simplified RICE/DICE IAM)", fontsize=13)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    path = os.path.join(OUT_DIR, "fig1_global_emissions_by_ssp.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved -> {path}")
    plt.show()

# FIGURE 2: Global + regional breakdown for one scenario
def plot_regional_emissions(res: dict, top_n: int = TOP_N) -> None:
    years    = res["years"]
    regional = res["emissions"]       # (N_REGIONS, n_years)
    global_e = res["global_emissions"]

    # Pick the top-N regions by peak annual emission
    peak_idx = np.argsort(regional.max(axis=1))[::-1][:top_n]
    colors   = cm.tab10(np.linspace(0, 1, top_n))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
    fig.suptitle(f"CO₂ Emissions — {res['ssp_name']}\n"
                 f"(Simplified RICE/DICE IAM)", fontsize=13)

    ax1.plot(years, global_e, color=res["ssp_color"],
             linewidth=2.4, label="Global total")
    ax1.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax1.set_ylabel("GtCO₂ / yr", fontsize=11)
    ax1.set_title("Global CO₂ Emissions", fontsize=11)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    for color, idx in zip(colors, peak_idx):
        ax2.plot(years, regional[idx], color=color,
                 linewidth=1.9, label=REGIONS[idx])
    ax2.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax2.set_ylabel("GtCO₂ / yr", fontsize=11)
    ax2.set_xlabel("Year", fontsize=11)
    ax2.set_title(f"Top-{top_n} Highest-Emitting Regions", fontsize=11)
    ax2.legend(fontsize=9, ncol=2, loc="upper right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUT_DIR,
                        f"fig2_regional_emissions_{res['ssp']}.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved -> {path}")
    plt.show()


# FIGURE 3: Temperature trajectories — all SSPs
def plot_temperature(results: dict) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))

    for ssp_key, res in results.items():
        color = res["ssp_color"]
        years = res["years"]
        # Ensemble mean line
        ax.plot(years, res["temperature"],
                color=color, linewidth=2.2, label=res["ssp_name"])
        if res.get("ensemble_size", 1) > 1:
            ax.fill_between(years,
                            res["temperature_p5"],
                            res["temperature_p95"],
                            color=color, alpha=0.15)

    # Paris Agreement reference lines
    for t_ref, ls, label in [
        (1.5, "--",  "1.5 degC"),
        (2.0, "-.",  "2.0 degC"),
        (3.0, ":",   "3.0 degC"),
    ]:
        ax.axhline(t_ref, color="dimgrey", linewidth=0.9,
                   linestyle=ls, label=label)

    # Note ensemble size
    n_ens = next(iter(results.values())).get("ensemble_size", 1)
    ens_note = f"  (shading = 5th\u201395th pct, n={n_ens})" if n_ens > 1 else ""
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("degC above pre-industrial (1850-1900)", fontsize=12)
    ax.set_title(f"Global Mean Temperature by SSP\n"
                 f"(Simplified RICE/DICE IAM{ens_note})", fontsize=13)
    ax.legend(fontsize=9, loc="upper left", ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    path = os.path.join(OUT_DIR, "fig3_temperature_by_ssp.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved -> {path}")
    plt.show()

# FIGURE 4: Regional emissions heatmap at target year
def plot_heatmap(results: dict, target_year: int = HEATMAP_YEAR) -> None:
    ssp_keys  = list(results.keys())
    ssp_labels = [SSP_CONFIGS[k]["name"].split("–")[0].strip()
                  for k in ssp_keys]

    data = np.zeros((N_REGIONS, len(ssp_keys)))
    for j, key in enumerate(ssp_keys):
        res = results[key]
        ti  = int(np.searchsorted(res["years"], target_year))
        ti  = min(ti, res["emissions"].shape[1] - 1)
        data[:, j] = res["emissions"][:, ti]

    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn_r", vmin=0)
    ax.set_xticks(range(len(ssp_keys)))
    ax.set_xticklabels(ssp_labels, fontsize=11)
    ax.set_yticks(range(N_REGIONS))
    ax.set_yticklabels(REGIONS, fontsize=10)
    ax.set_title(f"Regional CO₂ Emissions in {target_year} (GtCO₂/yr)\n"
                 f"(Simplified RICE/DICE IAM)", fontsize=12)
    plt.colorbar(im, ax=ax, label="GtCO₂ / yr", shrink=0.8)

    for i in range(N_REGIONS):
        for j in range(len(ssp_keys)):
            ax.text(j, i, f"{data[i, j]:.1f}",
                    ha="center", va="center", fontsize=8,
                    color="black" if data[i, j] < data.max() * 0.7 else "white")

    plt.tight_layout()
    path = os.path.join(OUT_DIR, f"fig4_heatmap_{target_year}.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved -> {path}")
    plt.show()

# MAIN
def main():
    print("=" * 60)
    print("  Simplified RICE/DICE Integrated Assessment Model")
    print("=" * 60)

    results = {}
    for ssp_key in SSP_CONFIGS:
        name = SSP_CONFIGS[ssp_key]['name'].replace('\u2013', '-')
        print(f"\n  Running {ssp_key}: {name} ...")
        results[ssp_key] = run_iam(
            ssp_key    = ssp_key,
            start_year = START_YEAR,
            end_year   = END_YEAR,
        )

    print(f"\n{'-'*62}")
    print(f"  {'Scenario':<38}  {'Emis. 2100 (GtCO2/yr)':>21}  {'dT 2100 (C)':>11}")
    print(f"  {'-'*38}  {'-'*21}  {'-'*11}")
    for key, res in results.items():
        e = res["global_emissions"][-1]
        t = res["temperature"][-1]
        name = res['ssp_name'].replace('\u2013', '-')
        print(f"  {name:<38}  {e:>21.1f}  {t:>11.2f}")
    print(f"{'-'*62}\n")

    print("Generating figures ...")
    plot_global_emissions(results)
    plot_regional_emissions(results[REGIONAL_SSP])
    plot_temperature(results)
    plot_heatmap(results, target_year=HEATMAP_YEAR)

    print("\nAll figures saved to:", OUT_DIR)

if __name__ == "__main__":
    main()
