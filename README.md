# When Tombs Speak 🏺

**A Streamlit digital humanities project about power, gender, inequality, and public memory in Chinese tomb archaeology.**

This website turns museum visits into a research project. It maps Chinese museums with tomb archaeology exhibits, records five-layer observations, calculates a **Tomb Inequality Index**, visualizes exhibit narratives, and generates constructive letters to museums.

## Features

- Interactive China map with museum points
- Editable museum database
- Five-layer analysis fields:
  - Archaeological Truth
  - Museum Framing
  - Visitor Perception
  - Ethical Question
  - Possible Change
- Data tags:
  - Power Narrative Intensity
  - Gender Perspective
  - Commoner Perspective
  - Labor Perspective
  - Reflective Narrative
  - Tomb Inequality Index
- Data visualization dashboard
- Museum observation cards
- Museum recommendation letter generator

## Project Structure

```text
tomb_archaeology_streamlit/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── data/
    └── museums.csv
```

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Create a GitHub repository.
2. Upload all files in this folder.
3. Go to Streamlit Community Cloud.
4. Choose your repository.
5. Set main file path as:

```text
app.py
```

6. Deploy.

## How to Add Data

Open the **Editable Database** tab and edit the table directly.

Important columns:

- `museum_name`: museum name
- `latitude`, `longitude`: map coordinates
- `period`: historical period
- `tomb_type`: tomb category
- `archaeological_truth`: what the tomb reveals
- `museum_framing`: how the museum explains it
- `visitor_perception`: how visitors respond
- `ethical_question`: modern ethical question
- `possible_change`: your recommendation

Scores should be from **0 to 5**.

## Tomb Inequality Index

```text
TII = 0.30 × Power Narrative
    + 0.20 × (5 - Gender Perspective)
    + 0.20 × (5 - Commoner Perspective)
    + 0.15 × (5 - Labor Perspective)
    + 0.15 × (5 - Reflective Narrative)
```

A higher score means the display may center elite power while giving less visibility to women, ordinary people, laborers, or reflective questions.

This index is interpretive, not absolute. It is meant to help viewers ask better questions.

## Suggested Research Workflow

1. Visit a museum's online exhibition.
2. Record basic information and coordinates.
3. Write five-layer observation notes.
4. Read public visitor comments and code them by theme.
5. Score the narrative dimensions.
6. Compare museums through the visualization dashboard.
7. Write a constructive letter to selected museums.

## Data Ethics

- Do not copy large amounts of visitor comments directly.
- Do not include usernames or personal information.
- Keep your coding criteria transparent.
- Write to museums respectfully and constructively.

## Suggested Project Description

> When Tombs Speak is a student-led digital humanities project that examines how Chinese museums frame tomb archaeology. Through an interactive map, narrative coding, visitor perception analysis, and a Tomb Inequality Index, the project asks whether museum exhibits merely celebrate ancient civilization or also help the public reflect on power, gender, labor, inequality, and memory.
