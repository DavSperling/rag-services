import json
import re
import sys
from datetime import datetime
from pathlib import Path

from scripts.check_evidence import load_questions, normalize
from scripts.generate import build_prompt, client, generate
from scripts.rerank import rerank
from scripts.search import search


def is_hit(evidence, results):
    textes = [normalize(r[0]) for r in results]
    return all(any(normalize(phrase) in texte for texte in textes) for phrase in evidence)


def judge(question, reference, answer):
    system_prompt = """You are an evaluator. You compare a generated answer against a reference answer.

Three possible verdicts:
- correct: contains the essential facts from the reference answer, without errors.
- partial: misses part of the essential facts, but contains no incorrect information.
- incorrect: contains an error, a contradiction, or is off-topic.

Important rules:
- Special rule for ABSTAIN: if the reference answer is "ABSTAIN", the answer is "correct" only if it explicitly refuses to answer due to lack of information. An answer providing factual information despite an ABSTAIN reference is "incorrect".
- Additional accurate information: additional accurate information beyond what is in the reference answer must NEVER lower the verdict. As long as the essential facts from the reference answer are present and nothing is false or contradictory, the verdict must be "correct". Only missing essential facts or false facts count against the answer.
- Length bias: a longer or more detailed answer than the reference is not necessarily better, but extra correct details must never penalize the answer.

Output format:
Respond ONLY with a JSON object: {"verdict": "correct|partial|incorrect", "reason": "One sentence explaining the decision."}
No markdown formatting, no code fence."""

    user_content = f"""Question: {question}
Reference answer: {reference}
Answer to evaluate: {answer}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            temperature=0,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
    except TypeError:
        response = client.messages.create(
            model="claude-haiku-4-5",
            extra_body={"temperature": 0},
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    # 1. Tentative de décodage JSON direct
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "verdict" in data:
            v = str(data["verdict"]).lower().strip()
            if v in ("correct", "partial", "incorrect"):
                return {"verdict": v, "reason": data.get("reason", "")}
    except json.JSONDecodeError:
        pass

    # 2. Extraction par regex stricte sur la clé verdict
    match = re.search(r'"verdict"\s*:\s*"(correct|partial|incorrect)"', text, re.IGNORECASE)
    if match:
        reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', text)
        reason = reason_match.group(1) if reason_match else text
        return {"verdict": match.group(1).lower(), "reason": reason}

    # 3. Fallback avec frontières de mots (\b) : tester 'incorrect' EN PREMIER !
    # (En Python, "correct" in "incorrect" vaut True, ce qui transformait les échecs en succès)
    lower = text.lower()
    if re.search(r"\bincorrect\b", lower):
        return {"verdict": "incorrect", "reason": text}
    if re.search(r"\bpartial\b", lower):
        return {"verdict": "partial", "reason": text}
    if re.search(r"\bcorrect\b", lower):
        return {"verdict": "correct", "reason": text}

    return {"verdict": "incorrect", "reason": text}


if __name__ == "__main__":
    # --- Tests du juge ---
    res1 = judge(
        "What is a fiscal year?",
        "12 consecutive months ending on the last day of any month except December.",
        "A fiscal year is 12 months ending on the last day of any month other than December.",
    )
    print("Test 1 (attendu: correct) :", res1)

    res2 = judge(
        "What is the capital of Peru?",
        "ABSTAIN",
        "The capital of Peru is Lima.",
    )
    print("Test 2 (attendu: incorrect) :", res2)

    res3 = judge(
        "What is the capital of Peru?",
        "ABSTAIN",
        "I cannot answer this question based on the provided context.",
    )
    print("Test 3 (attendu: correct) :", res3)

    # --- Étape 3 : Évaluation complète des 40 questions ---
    questions = load_questions("eval/questions.jsonl")
    records = []
    use_rerank = "--no-rerank" not in sys.argv

    mode_str = "RERANKING ACTIF (top 20 -> top 5 via Cross-Encoder)" if use_rerank else "SANS RERANKING (top 5 pgvector direct)"
    print(f"\n--- Évaluation en cours (40 questions) [{mode_str}] ---")
    for q in questions:
        if use_rerank:
            raw_candidates = search(q["question"], k=20)
            results = rerank(q["question"], raw_candidates, top_k=5)
        else:
            results = search(q["question"], k=5)

        if q["type"] != "out_of_scope":
            hit = is_hit(q["evidence"], results)
        else:
            hit = None

        prompt = build_prompt(q["question"], results)
        answer = generate(prompt)
        verdict_data = judge(q["question"], q["reference_answer"], answer)

        record = {
            "id": q["id"],
            "type": q["type"],
            "hit": hit,
            "answer": answer,
            "verdict": verdict_data.get("verdict"),
            "reason": verdict_data.get("reason"),
        }
        records.append(record)
        print(f"{q['id']} hit={hit} {record['verdict']}")

    # --- C. Le rapport ---
    non_oos = [r for r in records if r["hit"] is not None]
    hits = sum(1 for r in non_oos if r["hit"] is True)
    total_recall = len(non_oos)
    recall_pct = (hits / total_recall * 100) if total_recall > 0 else 0

    correct_count = sum(1 for r in non_oos if r["verdict"] == "correct")
    partial_count = sum(1 for r in non_oos if r["verdict"] == "partial")
    incorrect_count = sum(1 for r in non_oos if r["verdict"] == "incorrect")

    oos = [r for r in records if r["type"] == "out_of_scope"]
    oos_correct = sum(1 for r in oos if r["verdict"] == "correct")
    oos_total = len(oos)
    oos_pct = (oos_correct / oos_total * 100) if oos_total > 0 else 0

    croisement = [r["id"] for r in non_oos if r["hit"] is True and r["verdict"] != "correct"]

    print("\n" + "=" * 50)
    print("=== RAPPORT D'ÉVALUATION COMPLET ===")
    print("=" * 50)
    print(f"Recall@5 : {hits}/{total_recall} ({recall_pct:.1f} %)")
    print("\nQualité des réponses (35 questions hors out_of_scope) :")
    print(f"  - Correct   : {correct_count}/{total_recall} ({correct_count/total_recall*100:.1f} %)")
    print(f"  - Partial   : {partial_count}/{total_recall} ({partial_count/total_recall*100:.1f} %)")
    print(f"  - Incorrect : {incorrect_count}/{total_recall} ({incorrect_count/total_recall*100:.1f} %)")
    print(f"\nTaux d'abstention (5 out_of_scope) : {oos_correct}/{oos_total} ({oos_pct:.1f} %)")
    print(f"\nCroisement (hit=True mais verdict != correct) ({len(croisement)}) : {croisement}")

    # --- D. Sauvegarde ---
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    output_file = results_dir / f"{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"\nRésultats sauvegardés dans : {output_file}")