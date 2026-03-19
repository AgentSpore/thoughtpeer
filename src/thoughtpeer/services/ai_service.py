"""AI analysis service using OpenRouter (Gemini Flash).

Analyzes journal entries: extracts problems, emotions, category,
severity, keywords. Provides summary and actionable advice.
Falls back to keyword-based analysis if LLM unavailable.
"""

from __future__ import annotations

import json
import re

import httpx

from ..core.config import get_settings

SYSTEM_PROMPT = """You are ThoughtPeer AI — an empathetic, insightful journal analyst.
Analyze the user's journal entry and return a JSON object with:

{
  "problems": ["list of specific problems or challenges mentioned"],
  "emotions": ["list of emotions detected (e.g. anxiety, sadness, frustration, hope)"],
  "category": "one of: work, relationships, health, finance, self-growth, mental-health, family, education, creativity, general",
  "severity": <1-10 integer, where 1=minor annoyance, 10=crisis>,
  "keywords": ["important keywords for matching with peers"],
  "summary": "2-3 sentence empathetic summary of what the person is going through",
  "advice": "2-3 sentences of gentle, actionable advice based on their specific situation"
}

Rules:
- Be empathetic, never judgmental
- The summary should make the person feel heard and understood
- The advice should be specific and actionable, not generic platitudes
- Extract ALL emotions, even subtle ones
- Keywords should be useful for finding people with similar experiences
- Return ONLY valid JSON, no markdown formatting"""


async def analyze_entry(text: str, mood: str | None = None) -> dict:
    settings = get_settings()
    if settings.openrouter_api_key:
        try:
            return await _llm_analyze(text, mood, settings)
        except Exception:
            pass
    return _fallback_analyze(text)


async def _llm_analyze(text: str, mood: str | None, settings) -> dict:
    user_msg = f"Journal entry (mood: {mood or 'not specified'}):\n\n{text}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    # Extract JSON from response (handle markdown code blocks)
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        result = json.loads(json_match.group())
        # Validate expected fields
        return {
            "problems": result.get("problems", []),
            "emotions": result.get("emotions", ["neutral"]),
            "category": result.get("category", "general"),
            "severity": min(10, max(1, int(result.get("severity", 5)))),
            "keywords": result.get("keywords", []),
            "summary": result.get("summary", ""),
            "advice": result.get("advice", ""),
        }
    raise ValueError("No JSON in LLM response")


# --- Fallback (keyword-based) ---

EMOTION_KEYWORDS = {
    "anxiety": ["anxious", "worried", "nervous", "panic", "stress", "fear", "dread", "overwhelmed"],
    "sadness": ["sad", "depressed", "hopeless", "lonely", "grief", "cry", "miserable", "empty"],
    "anger": ["angry", "frustrated", "furious", "annoyed", "rage", "irritated", "mad", "resentful"],
    "joy": ["happy", "excited", "grateful", "proud", "content", "relieved", "glad", "thrilled"],
    "confusion": ["confused", "lost", "uncertain", "overwhelmed", "stuck", "unsure", "torn"],
    "guilt": ["guilty", "ashamed", "regret", "blame", "sorry", "fault"],
    "loneliness": ["alone", "isolated", "disconnected", "nobody", "abandoned", "invisible"],
    "hope": ["hope", "optimistic", "looking forward", "better", "improving", "progress"],
}

CATEGORY_KEYWORDS = {
    "work": ["job", "boss", "colleague", "deadline", "meeting", "project", "career", "office", "work", "promotion", "fired", "salary"],
    "relationships": ["partner", "friend", "friendship", "relationship", "dating", "breakup", "love", "trust", "marriage", "boyfriend", "girlfriend"],
    "health": ["health", "sleep", "exercise", "diet", "pain", "doctor", "sick", "tired", "energy", "weight", "insomnia", "headache"],
    "finance": ["money", "debt", "salary", "bills", "budget", "savings", "expensive", "afford", "rent", "loan", "credit"],
    "self-growth": ["learn", "habit", "goal", "motivation", "discipline", "procrastinate", "improve", "mindset", "skill", "growth"],
    "mental-health": ["therapy", "depression", "anxiety", "medication", "counseling", "coping", "mental", "therapist", "panic"],
    "family": ["parent", "mother", "father", "sibling", "brother", "sister", "child", "family", "son", "daughter"],
    "education": ["school", "university", "exam", "study", "grade", "professor", "class", "homework", "degree"],
}


def _fallback_analyze(text: str) -> dict:
    words = set(re.findall(r'\b\w+\b', text.lower()))

    emotions = [e for e, kws in EMOTION_KEYWORDS.items() if words & set(kws)] or ["neutral"]

    from collections import Counter
    cat_scores = Counter()
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = len(words & set(kws))
        if score:
            cat_scores[cat] = score
    category = cat_scores.most_common(1)[0][0] if cat_scores else "general"

    stopwords = {"this", "that", "with", "from", "have", "been", "were", "they",
                 "their", "about", "would", "could", "should", "which", "there",
                 "when", "what", "will", "just", "more", "some", "than", "them",
                 "very", "also", "into", "only", "other", "then", "these", "your"}
    keywords = [w for w in words if len(w) >= 4 and w not in stopwords][:15]

    sentences = re.split(r'[.!?]+', text)
    neg = {"not", "can't", "cannot", "don't", "won't", "never", "hate", "struggle",
           "problem", "issue", "difficult", "hard", "fail", "afraid", "worried", "stuck"}
    problems = [s.strip()[:200] for s in sentences if s.strip() and set(s.lower().split()) & neg][:5]

    severity = min(10, max(1, len(emotions) * 2 + len(problems)))

    return {
        "problems": problems,
        "emotions": emotions,
        "category": category,
        "severity": severity,
        "keywords": keywords,
        "summary": f"You seem to be dealing with {', '.join(emotions[:3])} related to {category}.",
        "advice": "Consider writing more about what specifically triggered these feelings. Sometimes articulating the problem is the first step to solving it.",
    }
