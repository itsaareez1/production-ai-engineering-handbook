"""Listing 18.2. Layout-aware extraction from OCR output, with routing.

Chapter 18, Knowledge Pipelines and the System of Record. Verified by
execution. The OCR output is a fixture: words with positions and
confidences, as an OCR engine or document-analysis service returns
them. The listing reconstructs reading order, finds the table, extracts
fields with a confidence, validates the arithmetic, and routes.
Run with: python run.py 18.2
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Word:
    text: str
    x: float      # left edge, fraction of page width
    y: float      # top edge, fraction of page height
    conf: float   # OCR confidence, 0..1


def lines(words, tol=0.006):
    """Group words into lines by vertical position, then order each
    line left to right: reading order for a single-column region."""
    rows = []
    for w in sorted(words, key=lambda w: (w.y, w.x)):
        if rows and abs(rows[-1][0].y - w.y) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w.x) for r in rows]


NUM = re.compile(r"^\d+(\.\d{2})?$")


def table_rows(rows):
    """A table row: a description followed by quantity, unit price,
    and amount columns (three numeric tokens at the right)."""
    out = []
    for r in rows:
        nums = [w for w in r if NUM.match(w.text)]
        if len(nums) >= 3 and nums[-1].x > 0.7:
            desc = " ".join(w.text for w in r if w not in nums[-3:])
            q, p, a = nums[-3:]
            out.append({"desc": desc, "qty": float(q.text),
                        "price": float(p.text),
                        "amount": float(a.text),
                        "conf": min(w.conf for w in r)})
    return out


def field(rows, label):
    """Value to the right of a label on the same line."""
    for r in rows:
        txt = [w.text.lower() for w in r]
        if label in txt:
            i = txt.index(label)
            vals = r[i + 1:]
            if vals:
                return (" ".join(w.text for w in vals),
                        min(w.conf for w in vals))
    return None, 0.0


def extract(words, floor=0.90):
    rows = lines(words)
    items = table_rows(rows)
    rec, problems = {"items": items}, []
    for name in ("invoice", "date", "total"):
        val, conf = field(rows, name + ":")
        rec[name] = val
        if val is None:
            problems.append(f"{name}: not found")
        elif conf < floor:
            problems.append(f"{name}: low OCR confidence {conf:.2f}")
    if rec["date"] and not re.match(r"\d{4}-\d{2}-\d{2}$", rec["date"]):
        problems.append(f"date: bad format {rec['date']!r}")
    for it in items:
        if abs(it["qty"] * it["price"] - it["amount"]) > 0.005:
            problems.append(f"line '{it['desc']}': qty x price "
                            f"!= amount")
    try:
        total = float(rec["total"])
        s = round(sum(it["amount"] for it in items), 2)
        if abs(s - total) > 0.005:
            problems.append(f"total {total:.2f} != lines {s:.2f}")
    except (TypeError, ValueError):
        problems.append(f"total: not a number {rec['total']!r}")
    rec["route"] = "review" if problems else "accept"
    return rec, problems


def page(total_text, total_conf):
    w = Word
    return [
        w("ACME", .08, .05, .99), w("Supplies", .16, .05, .99),
        w("Invoice:", .62, .05, .99), w("INV-2291", .74, .05, .98),
        w("Date:", .62, .08, .99), w("2026-10-14", .74, .08, .97),
        w("Paper", .08, .30, .98), w("A4", .15, .30, .97),
        w("10", .55, .30, .99), w("4.50", .66, .30, .98),
        w("45.00", .80, .30, .98),
        w("Toner", .08, .33, .98), w("cartridge", .16, .33, .96),
        w("2", .55, .33, .99), w("38.00", .66, .33, .97),
        w("76.00", .80, .33, .97),
        w("Total:", .62, .45, .99),
        w(total_text, .80, .45, total_conf),
    ]


if __name__ == "__main__":
    for name, words in [("clean scan", page("121.00", .97)),
                        ("poor scan", page("12B.00", .61))]:
        rec, problems = extract(words)
        print(f"{name}: route={rec['route']} invoice={rec['invoice']} "
              f"lines={len(rec['items'])} total={rec['total']}")
        for p in problems:
            print("   -", p)
