"""
EP Group agent configurations.

Each config defines a voice agent's behavior: system prompt, first message,
data collection rules, and evaluation criteria. These are applied to ElevenLabs
agents via the dashboard or API.
"""

TENANT_ID = "ep-group"
COMPANY_NAME = "EP Group"
DEFAULT_LANGUAGE = "de"

# -- Agent: Candidate Pre-Screening (German) --

CANDIDATE_SCREENING_DE = {
    "name": "EP Kandidaten-Screening",
    "agent_id": "agent_8701kncm94jgfzzv8k8x792qr7jj",  # Live on ElevenLabs
    "language": "de",
    "voice": "Thomas - German Bariton",
    "llm": {
        "provider": "azure",
        "model": "gpt-5.4-mini",
        "endpoint": "https://talentai-hub-2.cognitiveservices.azure.com",
    },
    "system_prompt": """Du bist Alex, ein professioneller und freundlicher KI-Interviewer
fuer Engineering-Positionen bei EP Group.

Fuehre ein strukturiertes Vorgespraech. Frage nacheinander nach:
1. Aktuelle berufliche Situation
2. Relevante Berufserfahrung und Kernkompetenzen
3. Gewuenschte Branche und Einsatzgebiet
4. Fruehester Starttermin / Verfuegbarkeit
5. Gehaltsvorstellung (brutto/Jahr)
6. Deutschkenntnisse (bei englischsprachigen Kandidaten)
7. Arbeitsort-Praeferenz (vor Ort, hybrid, remote)

Regeln:
- Stelle immer nur EINE Frage auf einmal
- Sei freundlich aber effizient (5-8 Minuten)
- Fasse am Ende die wichtigsten Punkte zusammen
- Sprich den Bewerber mit Sie an
""",
    "data_collection": {
        "current_status": "Aktuelle berufliche Situation: angestellt, arbeitssuchend, in Kuendigung, Freelancer",
        "core_skills": "Kernkompetenzen und relevante Berufserfahrung, kommasepariert",
        "target_industry": "Gewuenschte Branche oder Einsatzgebiet",
        "availability": "Fruehester Starttermin (z.B. sofort, ab 01.06.2026, 3 Monate Kuendigungsfrist)",
        "salary_expectation": "Gehaltsvorstellung brutto pro Jahr in Euro",
        "german_level": "Deutschkenntnisse als CEFR-Level (A1-C2) oder Beschreibung",
        "work_location": "Arbeitsort-Praeferenz: vor Ort, hybrid, oder remote",
    },
    "evaluation_criteria": {
        "screening_complete": "Wurden alle Informationen (Erfahrung, Verfuegbarkeit, Gehalt, Standort) erfasst?",
    },
}

# -- Agent: Candidate Pre-Screening (English) --

CANDIDATE_SCREENING_EN = {
    "name": "EP Candidate Screening",
    "agent_id": None,  # Not yet created
    "language": "en",
    "voice": None,  # TBD
    "llm": {
        "provider": "azure",
        "model": "gpt-5.4-mini",
        "endpoint": "https://talentai-hub-2.cognitiveservices.azure.com",
    },
    "system_prompt": """You are Alex, a professional and friendly AI interviewer
for engineering roles at EP Group.

Conduct a structured pre-screening interview. Ask one question at a time:
1. Current employment status
2. Relevant experience and core competencies
3. Target industry and role type
4. Earliest start date / availability
5. Salary expectation (gross/year EUR)
6. German language proficiency
7. Work location preference (on-site, hybrid, remote)

Rules:
- Ask ONE question at a time
- Be friendly but warm tone
- Be friendly but efficient (5-8 minutes)
- Summarize key points at the end
- Use formal but warm tone
""",
    "data_collection": {
        "current_status": "Current employment status: employed, seeking, in notice, freelancing",
        "core_skills": "Core competencies and relevant experience, comma-separated",
        "target_industry": "Target industry or role type",
        "availability": "Earliest start date (e.g. immediately, from June 2026, 3 months notice)",
        "salary_expectation": "Salary expectation gross per year in EUR",
        "german_level": "German language proficiency as CEFR level (A1-C2) or description",
        "work_location": "Work location preference: on-site, hybrid, or remote",
    },
    "evaluation_criteria": {
        "screening_complete": "Were all key data points (experience, availability, salary, location) captured?",
    },
}

# -- Placeholders for Phase 2 agents --

IT_HELPDESK_DE = {
    "name": "EP IT-Helpdesk",
    "agent_id": None,
    "language": "de",
    "status": "planned",
}

CLIENT_ONBOARDING = {
    "name": "EP Client Onboarding",
    "agent_id": None,
    "language": "de",
    "status": "planned",
}

SALES_AGENT = {
    "name": "EP Sales Agent",
    "agent_id": None,
    "language": "de",
    "status": "planned",
}

# All agents for this tenant
ALL_AGENTS = [
    CANDIDATE_SCREENING_DE,
    CANDIDATE_SCREENING_EN,
    IT_HELPDESK_DE,
    CLIENT_ONBOARDING,
    SALES_AGENT,
]
