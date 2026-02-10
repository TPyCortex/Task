import json
import os
from datetime import datetime


INPUT_PATH = os.environ.get("RESULTS_PATH", "output/results.json")
OUTPUT_PATH = os.environ.get("OUTREACH_PATH", "output/outreach_ready.json")


def load_results(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)


def generate_outreach_draft(trainer: dict) -> dict:

    name = trainer["trainer_name"].split("@")[0].replace(".", " ").title()
    quote = trainer["evidence_quotes"][0]["quote"] if trainer["evidence_quotes"] else "N/A"

    
    if len(quote) > 200:
        quote = quote[:197] + "..."

    subject = f"Your learners love your training — would you share your story?"

    body = f"""Hi {name},

I hope this message finds you well!

We've been reviewing learner feedback across our trainer network, and your name stood out. Your training sessions have received consistently strong feedback, with an overall rating of {trainer['overall_avg']}/10 across {trainer['n_responses']} responses.

Here's what one of your learners said:

  \"{quote}\"

We'd love to feature your journey in a short case study to inspire other trainers in our network. This would involve either:

  • A short testimonial quote (2–3 sentences, we can draft it for your approval), or
  • A 15–20 minute chat (or written Q&A) for a fuller case study

Would you be open to either of these? Happy to work around your schedule.

Thanks for the great work you do!

Best regards,
The Camphire Team"""

    return {
        "trainer_name": trainer["trainer_name"],
        "trainer_display_name": name,
        "subject": subject,
        "body": body,
        "trainer_score": trainer["trainer_score"],
        "n_responses": trainer["n_responses"],
        "case_study_angle": trainer["case_study_angle"],
        "generated_at": datetime.now().isoformat(),
        "status": "draft",
    }


def main():
    print("📧 Outreach Draft Generator")
    print("-" * 40)

    results = load_results(INPUT_PATH)
    print(f"✓ Loaded {len(results)} top trainers from {INPUT_PATH}")

    drafts = []
    for trainer in results:
        draft = generate_outreach_draft(trainer)
        drafts.append(draft)
        print(f"\n📬 Draft for: {draft['trainer_display_name']}")
        print(f"   Subject: {draft['subject']}")
        print(f"   Status: {draft['status']}")

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(drafts, f, indent=2)

    print(f"\n✓ Saved {len(drafts)} outreach drafts to {OUTPUT_PATH}")
    print("✅ Done! Ready for review or automation pickup.")


if __name__ == "__main__":
    main()
