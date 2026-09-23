"""m4rel — unsubstantiated absolute docstring claim (candidate, 22C).

Implements the relation frozen in
eval/evidence/v21-m4rel-prereg-2026-09-23/TARGETS_CONTRACT.json:

    an in-diff docstring/comment makes an absolute or exclusive claim
    about the behavior of code NOT present in the diff, where nothing
    in the change substantiates the claim and documenting that
    out-of-diff contract is the change's stated purpose.

Semantics over keywords: the quantifier vocabulary below is
ILLUSTRATIVE RECALL, not the detector. A clause fires only when ALL
of the following hold (the frozen semantic boundary):

  1. The clause carries a quantifying exclusivity marker and no
     disclaimer/hedge marker (self-scoped, hedged, or deferring
     clauses are never claims).
  2. The clause names an out-of-diff ACTOR (an external component
     such as an orchestrator or scheduler) that none of the change's
     defined symbols provide. Claims about generic in-diff behavior
     ("all errors are raised as X") name no external actor and are
     out of scope.
  3. Nothing in the change substantiates the claim: no other file in
     the diff imports and consumes the claimed module (the C3
     substantiation pattern — an in-diff enumerated referent with
     registered consumers is self-substantiating).
  4. The change's stated purpose is documentation (title/body).
  5. Requirement statements ("must not be silently masked") are not
     exclusivity claims and never fire.

Runtime sees fixture content only: no oracle roles, no source-record
or record-index branching. This module imports nothing from the
frozen Phase-17 verifier (eval/v21_contract_relations.py) and is not
a wrapper of any T3/T4 relation (22A QG3).

Holdout seal: per the 22B contract this implementation was developed
against corpus/in-sample material only. The fresh holdout at
eval/evidence/v21-m4rel-holdout-2026-09-23 was NOT executed against
during 22C; its first sanctioned execution is the separately reviewed
qualification phase.
"""
import re

NAME = "m4rel"
RELATION = "unsubstantiated_absolute_docstring_claim"
IMPLEMENTATION = "22C-impl-v1"

MARKERS = re.compile(
    r"\b(?:all|always|never|only|every|none|solely|exclusively|"
    r"guarantees?|nothing else|any configuration|conditionally never|"
    r"exactly\s+\d+|no\s+other)\b", re.I)
DISCLAIMERS = re.compile(
    r"(?:does\s+not\s+define|out\s+of\s+scope|outside\s+this|"
    r"belong(?:s)?\s+to|defined\s+by|governed\s+by|is\s+advisory|"
    r"advisory:|not\s+by\s+this|window\s+is\s+advisory)", re.I)
HEDGES = re.compile(
    r"\b(?:typically|usually|generally|often|may|might|can\s+vary|"
    r"in\s+the\s+default|defaults\s+to)\b", re.I)
DOC_PURPOSE = re.compile(
    r"\b(?:document|documents|documentation|contract|reference|"
    r"guide|convention)\b", re.I)
ACTORS = (
    "orchestrator", "scheduler", "daemon", "collector", "consumer",
    "watcher", "supervisor", "entrypoint", "caller", "client",
    "service", "worker", "publisher", "dispatcher", "runner",
    "aggregator", "indexer", "exporter", "ingester", "loader",
    "broker", "agent", "queue", "pipeline", "registry", "build",
    "deploy", "release", "monitor", "probe", "health",
)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
CLAUSE_SPLIT = re.compile(r"\s+(?:;|:|\u2014)\s+")
DEF_CLASS = re.compile(r"^\s*(?:class|def)\s+([A-Za-z_]\w*)", re.M)
DEF_ASSIGN = re.compile(r"^\s*([A-Za-z_]\w*)\s*=", re.M)
IMPORT_OF = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
DOCSTRING = re.compile(r'("""|\'\'\')(.*?)(?:\1)', re.S)
COMMENT = re.compile(r"(?:^|\s)#(.*)")


def _added_lines(patch):
    out = []
    new_ln = None
    for line in patch.splitlines():
        m = re.match(r"@@\s*-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?", line)
        if m:
            new_ln = int(m.group(1))
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            out.append((new_ln, line[1:]))
            if new_ln is not None:
                new_ln += 1
        elif line.startswith("-"):
            continue
        elif new_ln is not None:
            new_ln += 1
    return out


def _doc_text(added):
    body = "\n".join(text for _, text in added)
    parts = [m.group(2) for m in DOCSTRING.finditer(body)]
    parts += [m.group(1) for m in COMMENT.finditer(body)]
    return "\n".join(parts)


def _clauses(fixture, path):
    for f in fixture["input"]["files"]:
        if f["path"] != path:
            continue
        added = _added_lines(f["patch"])
        text = _doc_text(added)
        for sent in SENT_SPLIT.split(text):
            for clause in CLAUSE_SPLIT.split(sent):
                yield " ".join(clause.split()), added


def _symbols(fixture):
    syms = set()
    for f in fixture["input"]["files"]:
        stem = f["path"].rsplit("/", 1)[-1].split(".")[0]
        syms.add(stem.lower())
        body = "\n".join(
            line[1:] for line in f["patch"].splitlines()
            if line.startswith("+") and not line.startswith("+++"))
        syms |= {m.lower() for m in DEF_CLASS.findall(body)}
        syms |= {m.lower() for m in DEF_ASSIGN.findall(body)}
    return syms


def _imported_modules(fixture):
    mods = set()
    for f in fixture["input"]["files"]:
        body = "\n".join(
            line[1:] for line in f["patch"].splitlines()
            if line.startswith("+") and not line.startswith("+++"))
        for a, b in IMPORT_OF.findall(body):
            mods.add((a or b).lower())
    return mods


def _singular(word):
    return word[:-1] if word.endswith("s") else word


def _actors_in(clause):
    found = set()
    for tok in re.findall(r"(?<![\w-])([A-Za-z_]\w*)(?![\w-])", clause):
        s = _singular(tok.lower())
        if s in ACTORS:
            found.add(s)
    return found


def _clause_fires(clause, syms, substantiated):
    if not clause or DISCLAIMERS.search(clause) or HEDGES.search(clause):
        return None
    if not MARKERS.search(clause):
        return None
    actors = _actors_in(clause)
    if not actors:
        return None
    if substantiated:
        return None
    if actors & syms:
        return None
    return actors


def detect(fixture):
    """Return blocking findings for unsupported out-of-diff claims."""
    title = fixture["input"].get("title", "")
    body = fixture["input"].get("body", "")
    if not DOC_PURPOSE.search(title + " " + body):
        return []
    syms = _symbols(fixture)
    paths = [f["path"] for f in fixture["input"]["files"]]
    imported_modules = _imported_modules(fixture)
    findings = []
    for path in paths:
        stem = path.rsplit("/", 1)[-1].split(".")[0].lower()
        substantiated = any(
            mod == stem or mod.endswith("." + stem)
            for mod in imported_modules)
        added = _added_lines(next(
            f["patch"] for f in fixture["input"]["files"]
            if f["path"] == path))
        for clause, _ in _clauses(fixture, path):
            actors = _clause_fires(clause, syms, substantiated)
            if not actors:
                continue
            first = clause.split()[0][:12].lower()
            ln = next((ln for ln, text in added
                       if text.strip().lower().startswith(first)), None)
            findings.append({
                "file": path,
                "line": ln,
                "severity": "blocking",
                "comment": (
                    "Unsubstantiated absolute claim: the documentation "
                    "states that %s (referents: %s). %s is not part of "
                    "this change and nothing here substantiates the "
                    "exclusivity of the claim; since documenting this "
                    "contract is the change's stated purpose, the "
                    "unverifiable absolute claim is the defect." % (
                        clause, ", ".join(sorted(actors)),
                        "/".join(sorted(actors)))),
                "relation": RELATION,
                "claim_clause": clause,
                "actors": sorted(actors),
            })
            break
    return findings


def _norm_tokens(text):
    return re.findall(r"[a-z0-9_]+", text.lower())


def _grams(tokens, n=6):
    return {" ".join(tokens[i:i + n])
            for i in range(len(tokens) - n + 1)}


def covers(finding, fixture):
    """Row-level coverage: does this candidate's detection cover the
    blocking row (finding produced on this fixture)?"""
    fires = detect(fixture)
    if not fires:
        return False
    cmt_grams = _grams(_norm_tokens(finding.get("comment", "")))
    if not cmt_grams:
        return False
    for f in fires:
        if f["file"] != finding.get("file"):
            continue
        if _grams(_norm_tokens(f["claim_clause"])) & cmt_grams:
            return True
    return False


def file_matches(finding, fixture):
    """Looser diagnostic: same-file match without claim linkage.
    Reported separately in evidence; never used for gates."""
    return any(f["file"] == finding.get("file")
               for f in detect(fixture))
