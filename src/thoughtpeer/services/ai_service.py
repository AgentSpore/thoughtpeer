"""Server-side fallback analysis for web UI demo.

In production, analysis runs on-device via local LLM (e.g. Phi-3, Gemma 2B).
This module provides a lightweight keyword-based fallback when
the client doesn't send pre-computed insights.
"""

from __future__ import annotations

import re
from collections import Counter

EMOTION_KEYWORDS = {
    "anxiety": ["anxious", "worried", "nervous", "panic", "stress", "fear", "dread"],
    "sadness": ["sad", "depressed", "hopeless", "lonely", "grief", "cry", "miserable"],
    "anger": ["angry", "frustrated", "furious", "annoyed", "rage", "irritated", "mad"],
    "joy": ["happy", "excited", "grateful", "proud", "content", "relieved", "glad"],
    "confusion": ["confused", "lost", "uncertain", "overwhelmed", "stuck", "unsure"],
    "guilt": ["guilty", "ashamed", "regret", "blame", "sorry", "fault"],
    "loneliness": ["alone", "isolated", "disconnected", "nobody", "abandoned"],
}

CATEGORY_KEYWORDS = {
    "work": ["job", "boss", "colleague", "deadline", "meeting", "project", "career", "office", "work", "promotion"],
    "relationships": ["partner", "friend", "family", "relationship", "dating", "breakup", "love", "trust", "marriage"],
    "health": ["health", "sleep", "exercise", "diet", "pain", "doctor", "sick", "tired", "energy", "weight"],
    "finance": ["money", "debt", "salary", "bills", "budget", "savings", "expensive", "afford", "rent"],
    "self-growth": ["learn", "habit", "goal", "motivation", "discipline", "procrastinate", "improve", "mindset"],
    "mental-health": ["therapy", "depression", "anxiety", "medication", "counseling", "coping", "mental"],
}


def analyze_text(text: str) -> dict:
    words = set(re.findall(r'\b\w+\b', text.lower()))

    # Detect emotions
    emotions = []
    for emotion, kws in EMOTION_KEYWORDS.items():
        if words & set(kws):
            emotions.append(emotion)

    # Detect category
    cat_scores: Counter = Counter()
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = len(words & set(kws))
        if score:
            cat_scores[cat] = score
    category = cat_scores.most_common(1)[0][0] if cat_scores else "general"

    # Extract keywords (nouns-like: 4+ chars, not stopwords)
    stopwords = {"this", "that", "with", "from", "have", "been", "were", "they",
                 "their", "about", "would", "could", "should", "which", "there",
                 "when", "what", "will", "just", "more", "some", "than", "them",
                 "very", "also", "into", "only", "other", "then", "these", "your"}
    keywords = [w for w in words if len(w) >= 4 and w not in stopwords][:15]

    # Simple problems extraction (sentences with negative markers)
    sentences = re.split(r'[.!?]+', text)
    negative_markers = {"not", "can't", "cannot", "don't", "won't", "never", "hate",
                        "struggle", "problem", "issue", "difficult", "hard", "fail",
                        "afraid", "worried", "stuck", "frustrated"}
    problems = []
    for s in sentences:
        s = s.strip()
        if s and set(s.lower().split()) & negative_markers:
            problems.append(s[:200])
    problems = problems[:5]

    # Severity (1-10): more negative emotions = higher
    severity = min(10, max(1, len(emotions) * 2 + len(problems)))

    return {
        "problems": problems,
        "emotions": emotions or ["neutral"],
        "category": category,
        "severity": severity,
        "keywords": keywords,
    }
