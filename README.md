Trainer Scout
Identifies top-performing trainers from learner feedback data and generates outreach drafts for case studies/testimonials.
Setup
pip install pandas numpy
Place your feedback CSV in data/feedback.csv relative to the scripts. If your CSV is elsewhere, set the path:
# Windows PowerShell
$env:CSV_PATH="C:\path\to\your\file.csv"

# Mac/Linux
export CSV_PATH="/path/to/your/file.csv"
Run
python task1_trainer_scout.py
python task2_outreach.py
Task 1 must run before Task 2 since Task 2 reads output/results.json.
Outputs
All outputs go to output/:

1. results.json: Top 2 trainers with scores, quotes, and case study angles
   
2. report.html:  Visual report with trainer cards and full leaderboard
   
3. leaderboard.csv: All qualifying trainers ranked
   
4. outreach_ready.json: Email drafts ready for automation pickup

Scoring
trainer_score = 0.6 * overall_avg + 0.4 * late_half_avg

6 rating columns averaged per trainer (1-10 scale)
Responses split by date into early/late halves
Minimum 3 responses to qualify

Automation
outreach_ready.json can be consumed by n8n, Make, Zapier, or any tool that reads JSON. For n8n: Read File node > Split In Batches > Gmail/Google Sheets.
