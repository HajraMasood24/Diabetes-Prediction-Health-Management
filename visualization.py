"""
Exploratory data analysis: generates a 5-panel figure summarizing the
diabetes dataset (outcome balance, age/glucose distributions, feature
means by class, and correlation with the outcome).
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns

import config

TEAL = '#1D9E75'
CORAL = '#D85A30'


def load_data(csv_path=None):
    df = pd.read_csv(csv_path or config.DATASET_CSV_PATH)
    # Not used for visualization — drop if present, don't crash if it's already gone
    df = df.drop(columns=['HbA1c_level'], errors='ignore')
    return df


def _plot_outcome_distribution(ax, df):
    counts = df['diabetes'].value_counts().sort_index()
    total = len(df)
    non_diabetic_pct = (counts[0] / total) * 100
    diabetic_pct = (counts[1] / total) * 100

    wedges, _ = ax.pie(
        counts, colors=[TEAL, CORAL], startangle=90,
        wedgeprops=dict(width=0.5, edgecolor='white', linewidth=2),
    )
    ax.set_title('Outcome distribution')
    ax.legend(
        wedges,
        [
            f'Non-diabetic  {counts[0]:,} ({non_diabetic_pct:.1f}%)',
            f'Diabetic  {counts[1]:,} ({diabetic_pct:.1f}%)',
        ],
        loc='lower center', bbox_to_anchor=(0.5, -0.15),
        frameon=False, fontsize=8, ncol=2,
    )


def _plot_age_distribution(ax, df):
    bins = range(0, 85, 5)
    for outcome, color, label in [(0, TEAL, 'Non-diabetic'), (1, CORAL, 'Diabetic')]:
        ax.hist(
            df[df['diabetes'] == outcome]['age'], bins=bins,
            alpha=0.55, color=color, edgecolor=color, linewidth=0.8, label=label,
        )
    ax.set_title('Age distribution by class')
    ax.set_xlabel('Age (years)')
    ax.set_ylabel('Count')
    ax.legend(frameon=False, fontsize=9)


def _plot_glucose_distribution(ax, df):
    for outcome, color, label in [(0, TEAL, 'Non-diabetic'), (1, CORAL, 'Diabetic')]:
        subset = df[df['diabetes'] == outcome]['blood_glucose_level']
        ax.hist(
            subset, bins=30, alpha=0.45, color=color, edgecolor=color,
            linewidth=0.8, density=True, label=label,
        )
        subset.plot.kde(ax=ax, color=color, linewidth=2, label='')
    ax.set_title('Blood glucose distribution by class')
    ax.set_xlabel('Blood Glucose (mg/dL)')
    ax.set_ylabel('Density')
    ax.legend(frameon=False, fontsize=9)


def _plot_feature_means(ax, df):
    features = ['blood_glucose_level', 'bmi', 'age']
    means = df.groupby('diabetes')[features].mean()

    x = np.arange(len(features))
    w = 0.35
    bars0 = ax.bar(x - w/2, means.loc[0], w, color=TEAL, alpha=0.7,
                    label='Non-diabetic', edgecolor=TEAL, linewidth=0.8, zorder=3)
    bars1 = ax.bar(x + w/2, means.loc[1], w, color=CORAL, alpha=0.7,
                    label='Diabetic', edgecolor=CORAL, linewidth=0.8, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(features, fontsize=10)
    ax.set_title('Feature means by class', fontsize=11, fontweight='bold')
    ax.set_ylabel('Mean value')
    ax.legend(frameon=False, fontsize=9, loc='upper right')
    ax.yaxis.grid(True, color='lightgray', linewidth=0.5, zorder=0)

    for bar in list(bars0) + list(bars1):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + (h * 0.02), f'{h:.1f}',
                ha='center', va='bottom', fontsize=9, color='#444', fontweight='bold')


def _plot_correlation(ax, df):
    numeric_cols = ['age', 'hypertension', 'heart_disease', 'bmi', 'blood_glucose_level']
    corr = df[numeric_cols + ['diabetes']].corr()['diabetes'].drop('diabetes').sort_values()

    bar_colors = [CORAL if v > 0.3 else '#EF9F27' if v > 0.15 else '#888780' for v in corr]

    ax.barh(corr.index, corr.values, color=bar_colors, edgecolor='none', height=0.65, zorder=3)
    ax.axvline(0, color='gray', linewidth=0.8)
    ax.set_title('Correlation with diabetes outcome', fontsize=11, fontweight='bold')
    ax.set_xlabel('Pearson r')
    ax.tick_params(axis='y', labelsize=7)
    ax.xaxis.grid(True, color='lightgray', linewidth=0.5, zorder=0)

    for val, feat in zip(corr.values, corr.index):
        ax.text(val + 0.005, feat, f'{val:.3f}', va='center', fontsize=9)


def build_eda_figure(df, output_path='diabetes_eda.png', show=True):
    """Build the 5-panel EDA figure, save it to output_path, and optionally display it."""
    sns.set_theme(style='whitegrid', font='DejaVu Sans')
    plt.rcParams.update({
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.titlesize': 11,
        'axes.titleweight': 'bold',
        'axes.titlepad': 10,
        'font.size': 10,
    })

    fig = plt.figure(figsize=(18, 9))
    fig.suptitle('Diabetes Dataset — Exploratory Data Analysis', fontsize=15, fontweight='bold', y=0.98)

    gs = gridspec.GridSpec(
        2, 3, figure=fig, hspace=0.35, wspace=0.38,
        top=0.90, bottom=0.10, left=0.07, right=0.97, width_ratios=[0.6, 1, 1],
    )
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, :2])
    ax5 = fig.add_subplot(gs[1, 2])

    _plot_outcome_distribution(ax1, df)
    _plot_age_distribution(ax2, df)
    _plot_glucose_distribution(ax3, df)
    _plot_feature_means(ax4, df)
    _plot_correlation(ax5, df)

    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"Saved figure to {output_path}")

    if show:
        plt.show()

    return fig


if __name__ == '__main__':
    dataset = load_data()
    build_eda_figure(dataset)
