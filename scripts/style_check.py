#!/usr/bin/env python3
"""Mechanical checks for ARTICLE_STYLE.md.

Usage: python3 scripts/style_check.py drafts/{id}/article_draft.md

Rules a grep can settle are settled here, so a draft is never passed on
somebody's impression of it. Everything this prints as FAIL is a spec
violation; WARN is a judgment call the writer has to look at.
"""
import re, sys, statistics

HEDGES = r"\b(although|though|while|however|arguably|somewhat|relatively|likely|may|might|could|appears?|seems?|suggests?|tends? to|not necessarily)\b"
BANNED = r"\b(delve[sd]?|delving|landscape|testament to|boasts?|underscore[sd]?|intricate|meticulous|pivotal|it'?s worth noting|in conclusion|at the end of the day|marks a (new|major|pivotal)|stands as|enduring legacy)\b"
PHANTOM = r"\b(experts?|observers?|analysts?|critics?|industry watchers|sources)\s+(say|said|argue|argued|note|noted|believe|suggest)\b"
NOTJUST = r"\b(is|are|was|were|it'?s|its)\s+not\s+(just|only|merely|about)\b"
DRESSED = r"\b(serves? as|plays? an? \w+ role|is designed to|acts? as a)\b"
CAVEAT = r"\b(it is important to (note|remember)|it should be noted|readers should)\b"

def main(path):
    raw = open(path).read()
    body = raw.split('---', 2)[2] if raw.startswith('---') else raw
    cta = ('Subscribe free', 'companion app Liftoff', 'Want more than the weekly')
    lines = [l for l in body.split('\n') if not any(c in l for c in cta)]
    body = '\n'.join(lines)
    plain = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', body)
    words = len(plain.split())
    fails = warns = 0

    def check(ok, label, detail=''):
        nonlocal fails
        print(('  PASS  ' if ok else '  FAIL  ') + label + (('  ' + detail) if detail and not ok else ''))
        if not ok: fails += 1

    def warn(ok, label, detail=''):
        nonlocal warns
        print(('  PASS  ' if ok else '  WARN  ') + label + (('  ' + detail) if detail and not ok else ''))
        if not ok: warns += 1

    print(f"\n{path}\n  {words} words excluding CTAs\n")
    check(900 <= words <= 1300, "word count 900-1300", f"got {words}")

    em = plain.count('—') - plain.count('Liftoff —')
    check(em == 0, "no em dashes outside the Liftoff title", f"{em} found")

    subs = re.findall(r'^## (.+)$', body, re.M)
    bad = [s for s in subs if re.match(r'(What|Why|How|When|Where|Who)\b', s)]
    check(not bad, "no interrogative subheads", str(bad))
    longsub = [s for s in subs if len(s.split()) > 5]
    warn(not longsub, "subheads two to five words", str(longsub))

    for label, pat in (("banned vocabulary", BANNED), ("phantom experts", PHANTOM),
                       ("'not just X but Y'", NOTJUST), ("dressed-up verbs", DRESSED),
                       ("unnecessary caveats", CAVEAT)):
        hits = re.findall(pat, plain, re.I)
        check(not hits, f"no {label}", str(hits[:4]))

    # Rhythm. Paragraph uniformity is this publication's measured weak spot.
    paras = [p.strip() for p in body.split('\n\n')
             if p.strip() and not p.startswith(('#', '---', '!', '**'))]
    plens = [len(p.split()) for p in paras]
    if len(plens) > 3:
        cv = statistics.pstdev(plens) / statistics.mean(plens)
        check(cv >= 0.35, "paragraph length varies (CV >= 0.35)", f"CV {cv:.2f}")
        run = longest = 1
        for i in range(1, len(plens)):
            a, b = plens[i-1], plens[i]
            run = run + 1 if a and abs(a-b)/max(a, b) <= 0.10 else 1
            longest = max(longest, run)
        check(longest < 3, "no 3 consecutive near-equal paragraphs", f"run of {longest}")

    sents = [s for s in re.split(r'(?<=[.!?])\s+', plain) if len(s.split()) > 2]
    slens = [len(s.split()) for s in sents]
    if len(slens) > 10:
        scv = statistics.pstdev(slens) / statistics.mean(slens)
        check(scv >= 0.45, "sentence length varies (CV >= 0.45)", f"CV {scv:.2f}")
        short = sum(1 for x in slens if x < 10) / len(slens)
        check(short >= 0.10, "at least 10% short sentences (<10 words)", f"{short:.0%}")

    hedges = len(re.findall(HEDGES, plain, re.I))
    rate = hedges / words * 100
    check(rate <= 1.2, "hedge density <= 1.2 per 100 words", f"{rate:.1f}")

    print(f"\n  {fails} FAIL, {warns} WARN\n")
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
