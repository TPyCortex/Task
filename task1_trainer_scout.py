
import pandas as pd
import numpy as np
import json
import sys
import os
from datetime import datetime

MIN_RESPONSES = 3          
TOP_N = 2                  
CSV_PATH = os.environ.get("CSV_PATH", "data/feedback.csv")


RATING_COLS = [
    "1.3_The trainer\u2019s teaching style helped me to stay concentrated.*",
    "1.4_The trainer offered the opportunity to participate.*",
    "2.8_The trainer was helpful in explaining how to put theory into practice.*",
    "v1_1.2_I perceived the trainer as concentrated.*",
    "v2_1.1_I perceived the trainer as motivated.*",
    "v2_1.2_ The trainer was very clear in their explanations.*",
]

QUOTE_COLS = [
    "3.12_What did you like most about their training style?*",
    "3.13_Could you please share a highlight from the training? What stood out to you as particularly enjoyable or beneficial?*",
    "2.6_Did the trainer establish good rapport with the learners? Did they make you feel at ease to ask question, interact, and\xa0engage with the training? Give details.*",
]


def load_and_clean(csv_path: str) -> pd.DataFrame:
    """Load CSV, clean it, and add stable row_id."""
    df = pd.read_csv(csv_path)

    
    df["row_id"] = ["ROW-" + str(i + 1).zfill(3) for i in range(len(df))]

    
    df["date"] = pd.to_datetime(df["Creation Date"], format="%b %d, %Y %I:%M %p", errors="coerce")
    
    
    nat_count = df["date"].isna().sum()
    if nat_count > 0:
        print(f"⚠ Warning: {nat_count} dates failed to parse and were coerced to NaT.")
        print(df[df["date"].isna()]["Creation Date"].unique()[:5])


    df = df[df["completed"].str.strip().str.lower() == "yes"].copy()

    
    for col in RATING_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    print(f"✓ Loaded {len(df)} completed responses for {df['Trainer'].nunique()} trainers")
    return df


def compute_trainer_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score each trainer. The score is:
      - average of all rating columns (weighted equally)
    
    We also compute an 'improvement' indicator by comparing
    the trainer's earlier-half avg score to their later-half avg score.
    """
    results = []

    for trainer, group in df.groupby("Trainer"):
        n = len(group)
        if n < MIN_RESPONSES:
            continue

        
        rating_means = group[RATING_COLS].mean()
        overall_score = rating_means.mean()

        
        group_sorted = group.sort_values("date")
        mid = len(group_sorted) // 2
        if mid > 0:
            early_scores = group_sorted.iloc[:mid][RATING_COLS].mean().mean()
            late_scores = group_sorted.iloc[mid:][RATING_COLS].mean().mean()
            improvement = late_scores - early_scores
        else:
            early_scores = overall_score
            late_scores = overall_score
            improvement = 0.0

        results.append({
            "trainer": trainer,
            "n_responses": n,
            "overall_score": round(overall_score, 2),
            "early_avg": round(early_scores, 2),
            "late_avg": round(late_scores, 2),
            "improvement": round(improvement, 2),
            "raw_combined": overall_score,  
        })

    scores_df = pd.DataFrame(results)

    if len(scores_df) == 0:
        print("⚠ No trainers met the minimum response threshold!")
        sys.exit(1)


    scores_df["trainer_score"] = (
        0.6 * scores_df["overall_score"] + 0.4 * scores_df["late_avg"]
    ).round(2)

    scores_df = scores_df.sort_values("trainer_score", ascending=False).reset_index(drop=True)
    return scores_df


def extract_best_quotes(df: pd.DataFrame, trainer: str, n_quotes: int = 2) -> list:
    """Pull the best (longest, most substantive) positive quotes for a trainer."""
    group = df[df["Trainer"] == trainer]
    candidates = []

    for _, row in group.iterrows():
        for col in QUOTE_COLS:
            val = row.get(col)
            if pd.notna(val) and isinstance(val, str) and len(val.strip()) > 20:
                candidates.append({
                    "row_id": row["row_id"],
                    "quote": val.strip().replace("\n", " "),
                    "source_column": col.split("_")[0],
                    "length": len(val.strip()),
                })

    candidates.sort(key=lambda x: x["length"], reverse=True)
    return candidates[:n_quotes]


def generate_case_study_angle(trainer: str, score_row: dict) -> str:
    """Generate a one-liner explaining why we should reach out."""
    if score_row["improvement"] > 0:
        return (
            f"Strong overall performance (avg {score_row['overall_score']}/10 across {score_row['n_responses']} reviews) "
            f"with visible improvement over time (+{score_row['improvement']} pts). "
            f"Great candidate for a 'growth journey' testimonial."
        )
    else:
        return (
            f"Consistently high performer (avg {score_row['overall_score']}/10 across {score_row['n_responses']} reviews). "
            f"Ideal for a 'best practices' case study."
        )


def build_results(df: pd.DataFrame, scores_df: pd.DataFrame, top_n: int = TOP_N) -> list:
    """Build the final Top N results with quotes and case study angles."""
    top_trainers = scores_df.head(top_n)
    results = []

    for _, row in top_trainers.iterrows():
        trainer = row["trainer"]
        quotes = extract_best_quotes(df, trainer)
        angle = generate_case_study_angle(trainer, row.to_dict())

        results.append({
            "rank": len(results) + 1,
            "trainer_name": trainer,
            "n_responses": int(row["n_responses"]),
            "trainer_score": float(row["trainer_score"]),
            "overall_avg": float(row["overall_score"]),
            "improvement": float(row["improvement"]),
            "evidence_quotes": [
                {"row_id": q["row_id"], "quote": q["quote"]} for q in quotes
            ],
            "case_study_angle": angle,
        })

    return results


def save_json(results: list, path: str):
    """Save results to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"✓ Saved {path}")


def save_html_report(results: list, scores_df: pd.DataFrame, path: str):
    """Generate a simple HTML report."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Most Improved Trainer Scout — Results</title>
<style>
  body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; background: #f8f9fa; color: #333; }
  h1 { color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }
  h2 { color: #e94560; margin-top: 40px; }
  .trainer-card { background: #fff; border-radius: 12px; padding: 24px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  .rank { font-size: 2em; font-weight: bold; color: #e94560; float: left; margin-right: 16px; }
  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 16px 0; }
  .stat { background: #f0f0f5; border-radius: 8px; padding: 12px; text-align: center; }
  .stat-value { font-size: 1.4em; font-weight: bold; color: #1a1a2e; }
  .stat-label { font-size: 0.85em; color: #666; }
  .quote { background: #fffde7; border-left: 4px solid #ffc107; padding: 12px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; font-style: italic; }
  .quote .row-id { font-style: normal; font-size: 0.8em; color: #999; }
  .angle { background: #e8f5e9; padding: 12px 16px; border-radius: 8px; margin-top: 12px; }
  table { width: 100%; border-collapse: collapse; margin: 20px 0; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
  th { background: #1a1a2e; color: #fff; padding: 12px; text-align: left; }
  td { padding: 10px 12px; border-bottom: 1px solid #eee; }
  tr:hover { background: #f5f5f5; }
  .footer { text-align: center; color: #999; margin-top: 40px; font-size: 0.85em; }
</style>
</head>
<body>
<h1>🏆 Most Improved Trainer Scout</h1>
<p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M") + """</p>
"""

    # Top trainer cards
    for r in results:
        html += f"""
<div class="trainer-card">
  <div class="rank">#{r['rank']}</div>
  <h2>{r['trainer_name']}</h2>
  <div class="stats">
    <div class="stat"><div class="stat-value">{r['trainer_score']}</div><div class="stat-label">Trainer Score</div></div>
    <div class="stat"><div class="stat-value">{r['overall_avg']}/10</div><div class="stat-label">Overall Average</div></div>
    <div class="stat"><div class="stat-value">{r['n_responses']}</div><div class="stat-label">Responses</div></div>
  </div>
  <div class="stats">
    <div class="stat"><div class="stat-value">{'+' if r['improvement'] >= 0 else ''}{r['improvement']}</div><div class="stat-label">Improvement (early→late)</div></div>
  </div>
  <h3>📝 Evidence Quotes</h3>
"""
        for q in r["evidence_quotes"]:
            html += f'  <div class="quote">"{q["quote"]}" <span class="row-id">[{q["row_id"]}]</span></div>\n'

        html += f'  <div class="angle">💡 <strong>Case Study Angle:</strong> {r["case_study_angle"]}</div>\n'
        html += "</div>\n"

    html += """
<h2>📊 Full Trainer Leaderboard</h2>
<table>
<tr><th>#</th><th>Trainer</th><th>Score</th><th>Avg Rating</th><th>Improvement</th><th>Responses</th></tr>
"""
    for i, row in scores_df.iterrows():
        html += f"<tr><td>{i+1}</td><td>{row['trainer']}</td><td><strong>{row['trainer_score']}</strong></td><td>{row['overall_score']}/10</td><td>{'+' if row['improvement'] >= 0 else ''}{row['improvement']}</td><td>{row['n_responses']}</td></tr>\n"

    html += """</table>
<div class="footer">
  <p>Score = 60% overall rating avg + 40% normalised improvement | Min responses: """ + str(MIN_RESPONSES) + """</p>
</div>
</body></html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Saved {path}")


def print_console_results(results: list):
    """Pretty-print results to terminal."""
    print("\n" + "=" * 70)
    print("🏆  TOP 2 TRAINERS — MOST IMPROVED / BEST PERFORMERS")
    print("=" * 70)

    for r in results:
        print(f"\n#{r['rank']}  {r['trainer_name']}")
        print(f"    Score: {r['trainer_score']}  |  Avg: {r['overall_avg']}/10  |  Improvement: {'+' if r['improvement'] >= 0 else ''}{r['improvement']}  |  Responses: {r['n_responses']}")
        print(f"    Quotes:")
        for q in r["evidence_quotes"]:
            short = q["quote"][:120] + "..." if len(q["quote"]) > 120 else q["quote"]
            print(f'      [{q["row_id"]}] "{short}"')
        print(f"    Angle: {r['case_study_angle']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("🔍 Most Improved Trainer Scout")
    print("-" * 40)

    df = load_and_clean(CSV_PATH)

    scores_df = compute_trainer_scores(df)

    
    results = build_results(df, scores_df)

    
    os.makedirs("output", exist_ok=True)
    print_console_results(results)
    save_json(results, "output/results.json")
    save_html_report(results, scores_df, "output/report.html")


    scores_df.to_csv("output/leaderboard.csv", index=False)
    print("✓ Saved output/leaderboard.csv")
    print("\n✅ Done! Check the output/ folder.")
