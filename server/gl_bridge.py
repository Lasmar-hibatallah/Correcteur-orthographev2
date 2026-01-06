# server/gl_bridge.py
import sys
import os
import json
import traceback
import re
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _word_count(s: str) -> int:
    return len([w for w in re.split(r"\s+", (s or "").strip()) if w])


def _flatten_suggestions(v):
    if not v:
        return []
    if isinstance(v, list):
        out = []
        for item in v:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, list):
                out.extend([x for x in item if isinstance(x, str)])
        return out
    return []


def _all_suggestions(err: dict):
    for k in ("aSuggestions", "aSugg", "suggestions"):
        if k in err:
            return _flatten_suggestions(err.get(k))
    return []


def _pick_list(parsed: dict, *keys):
    for k in keys:
        v = parsed.get(k)
        if isinstance(v, list):
            return v
    return []


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    a, b = a.lower(), b.lower()
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _is_only_diacritics_change(excerpt: str, suggestion: str) -> bool:
    ex = (excerpt or "").strip()
    su = (suggestion or "").strip()
    if not ex or not su:
        return False
    return _strip_diacritics(ex.lower()) == _strip_diacritics(su.lower()) and ex.lower() != su.lower()


def _is_spelling_suggestion_plausible(excerpt: str, suggestion: str) -> bool:
    """
    Filtre anti-suggestions farfelues, MAIS:
    - accepte toujours les corrections d'accents
    - accepte les mots courts si ratio <= 0.60
    - accepte les mots longs si ratio <= 0.60
    """
    ex = (excerpt or "").strip()
    su = (suggestion or "").strip()
    if not ex or not su:
        return False

    if _is_only_diacritics_change(ex, su):
        return True

    ex_l = ex.lower()
    su_l = su.lower()

    dist = _levenshtein(ex_l, su_l)
    denom = max(len(ex_l), len(su_l))
    ratio = dist / denom if denom else 1.0

    if denom <= 3:
        return ratio <= 0.60
    if denom >= 8:
        return ratio <= 0.60
    return ratio <= 0.50


def _best_spelling_suggestion(excerpt: str, suggs: list[str]) -> str:
    """
    Choisit la meilleure suggestion:
    1) priorité aux corrections d'accents (degats -> dégâts, ecole -> école)
    2) sinon: distance Levenshtein minimale
    3) tie-break: même première lettre
    """
    ex = (excerpt or "").strip()
    if not ex or not suggs:
        return ""

    # 1) accent-only gagne immédiatement
    for s in suggs:
        if _is_only_diacritics_change(ex, s):
            return s

    # 2) sinon: min distance
    ex_l = ex.lower()
    scored = []
    for s in suggs:
        s_l = (s or "").lower()
        if not s_l:
            continue
        d = _levenshtein(ex_l, s_l)
        same_first = 1 if (ex_l and s_l and ex_l[0] == s_l[0]) else 0
        scored.append((d, -same_first, s))

    if not scored:
        return ""

    scored.sort(key=lambda t: (t[0], t[1]))
    return scored[0][2]


def _classify(err: dict) -> str:
    msg = (err.get("sMessage") or err.get("message") or "").lower()
    rule = (err.get("sRuleId") or err.get("sRule") or "").lower()

    if ("conjug" in msg or "conjug" in rule or
        "participe" in msg or "participe" in rule or
        "infinitif" in msg or "infinitif" in rule):
        return "conjugaison"

    if ("ponctu" in msg or "ponctu" in rule or
        "virgule" in msg or "points" in msg or "point" in msg or
        "insécable" in msg or "numérisation" in msg):
        return "ponctuation"

    if ("apostrophe" in msg or "typograph" in msg or
        "majuscule" in msg or "surnum" in msg or "espace" in msg):
        return "style"

    if ("accord" in msg or "accord" in rule or
        "pluriel" in msg or "féminin" in msg or "masculin" in msg):
        return "grammaire"

    return "grammaire"


def _apply_replacements_by_index(text: str, reps):
    out = text
    reps_sorted = sorted(
        [r for r in reps if isinstance(r.get("start"), int) and isinstance(r.get("end"), int)],
        key=lambda r: r["start"],
        reverse=True,
    )
    for r in reps_sorted:
        s, e = r["start"], r["end"]
        repl = r.get("replace", "")
        repl = "" if repl is None else str(repl)
        if not repl:
            continue
        if 0 <= s <= e <= len(out):
            out = out[:s] + repl + out[e:]
    return out


def _to_masc_plural(adj: str) -> str:
    a = (adj or "").strip()
    if not a:
        return a
    low = a.lower()
    if low.endswith("s") or low.endswith("x"):
        return a
    if low.endswith("e") and len(low) > 2:
        a = a[:-1]
        low = a.lower()
    if low.endswith("al") and len(low) > 2:
        return a[:-2] + "aux"
    if low.endswith(("eau", "au", "eu")):
        return a + "x"
    return a + "s"


def _postprocess_coordination_agreement(corrected: str):
    added_issues = []
    text = corrected or ""

    pattern = re.compile(
        r"\bplusieurs\s+([A-Za-zÀ-ÖØ-öø-ÿ'-]+)\s+([A-Za-zÀ-ÖØ-öø-ÿ'-]+)\s+et\s+([A-Za-zÀ-ÖØ-öø-ÿ'-]+)\b",
        flags=re.IGNORECASE,
    )

    def repl(m: re.Match):
        nonlocal added_issues
        nom = m.group(1)
        adj1 = m.group(2)
        adj2 = m.group(3)

        new_adj1 = _to_masc_plural(adj1)
        new_adj2 = _to_masc_plural(adj2)

        if new_adj1 != adj1:
            added_issues.append({
                "type": "grammaire",
                "message": "Accord au pluriel après « plusieurs » (masculin pluriel).",
                "suggestion": new_adj1,
                "excerpt": adj1
            })
        if new_adj2 != adj2:
            added_issues.append({
                "type": "grammaire",
                "message": "Accord au pluriel dans une coordination (masculin pluriel).",
                "suggestion": new_adj2,
                "excerpt": adj2
            })

        return f"plusieurs {nom} {new_adj1} et {new_adj2}"

    new_text = pattern.sub(repl, text)
    return new_text, added_issues


def _should_ignore_a_to_a_grave(text: str, err: dict, grammar_list: list) -> bool:
    suggs = _all_suggestions(err)
    sugg = (suggs[0] if suggs else "").strip()
    if sugg != "à":
        return False

    start = int(err.get("nStart", -1))
    end = int(err.get("nEnd", -1))
    excerpt = text[start:end] if 0 <= start < end <= len(text) else ""
    if excerpt != "a":
        return False

    for e2 in grammar_list:
        msg2 = (e2.get("sMessage") or e2.get("message") or "").lower()
        rule2 = (e2.get("sRuleId") or e2.get("sRule") or "").lower()
        suggs2 = _all_suggestions(e2)
        best2 = (suggs2[0] if suggs2 else "").lower()

        if "participe" in msg2 or "participe" in rule2:
            return True
        if "avoir" in msg2 and "participe" in msg2:
            return True
        if re.search(r"(é|ée|és|ées)$", best2):
            return True

    return False


def main():
    try:
        raw_in = sys.stdin.read()
        data_in = json.loads(raw_in) if raw_in.strip().startswith("{") else {"text": raw_in}
        text = data_in.get("text", "")

        if not isinstance(text, str) or not text.strip():
            print(json.dumps({"error": "Texte vide."}, ensure_ascii=False))
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        grammalecte_parent = os.path.join(base_dir, "grammalecte")
        sys.path.insert(0, grammalecte_parent)

        import grammalecte
        gc = grammalecte.GrammarChecker("fr")

        errors_json_str = gc.getParagraphErrorsAsJSON(
            1,
            text,
            bContext=True,
            bSpellSugg=True,
            bReturnText=False
        )

        parsed = json.loads(errors_json_str) if errors_json_str else {}
        grammar_list = _pick_list(parsed, "lErrors", "lGrammarErrors")
        spelling_list = _pick_list(parsed, "lSpellingErrors", "lSpellErrors")

        issues = []
        replacements = []

        # --- Grammaire / conj / style / ponctuation ---
        for e in grammar_list:
            start = int(e.get("nStart", -1))
            end = int(e.get("nEnd", -1))
            msg = e.get("sMessage") or e.get("message") or "Erreur."
            suggs = _all_suggestions(e)
            sugg = (suggs[0] if suggs else "")
            excerpt = text[start:end] if 0 <= start < end <= len(text) else ""

            if _should_ignore_a_to_a_grave(text, e, grammar_list):
                continue

            t = _classify(e)

            issues.append({
                "type": t,
                "message": str(msg),
                "suggestion": str(sugg),
                "excerpt": excerpt
            })

            if sugg and 0 <= start < end <= len(text):
                replacements.append({"start": start, "end": end, "replace": str(sugg)})

        # --- Orthographe (BEST suggestion) ---
        for e in spelling_list:
            start = int(e.get("nStart", -1))
            end = int(e.get("nEnd", -1))
            msg = e.get("sMessage") or "Mot potentiellement mal orthographié."
            excerpt = (text[start:end] if 0 <= start < end <= len(text) else (e.get("sValue") or ""))

            suggs = _all_suggestions(e)
            best = _best_spelling_suggestion(excerpt, suggs)

            if best and not _is_spelling_suggestion_plausible(excerpt, best):
                best = ""

            issues.append({
                "type": "orthographe",
                "message": str(msg),
                "suggestion": str(best),
                "excerpt": excerpt
            })

            if best and 0 <= start < end <= len(text):
                replacements.append({"start": start, "end": end, "replace": str(best)})

        corrected_text = _apply_replacements_by_index(text, replacements)

        corrected_text, extra_issues = _postprocess_coordination_agreement(corrected_text)
        if extra_issues:
            issues.extend(extra_issues)

        by_type = {
            "orthographe": 0,
            "grammaire": 0,
            "conjugaison": 0,
            "ponctuation": 0,
            "style": 0,
            "autre": 0,
        }
        for it in issues:
            t = it.get("type", "autre")
            if t in by_type:
                by_type[t] += 1
            else:
                by_type["autre"] += 1

        out = {
            "correctedText": corrected_text,
            "issues": issues,
            "stats": {
                "words": _word_count(text),
                "total": len(issues),
                "byType": by_type
            }
        }

        print(json.dumps(out, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({
            "error": "Python bridge error",
            "details": str(e),
            "trace": traceback.format_exc()
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
