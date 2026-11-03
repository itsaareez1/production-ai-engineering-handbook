"""Listing 15.3. Full-text search with a permission filter in a
relational database (SQLite FTS5).

Chapter 15, Hybrid Retrieval. Verified by execution.
Run with: python run.py 15.3
"""
import sqlite3

con = sqlite3.connect(":memory:")
con.executescript("""
CREATE TABLE chunks(
  id TEXT PRIMARY KEY, document_id TEXT, content TEXT);
CREATE VIRTUAL TABLE chunks_fts USING fts5(
  content, content='chunks', content_rowid='rowid');
CREATE TABLE document_acl(document_id TEXT, group_id TEXT);
""")
rows = [
    ("leave-4.2", "policy-leave",
     "Unused annual leave may be carried forward up to five days."),
    ("forms-hr", "wiki-forms",
     "Use form HR-27 to request a leave carry-over exception."),
    ("pay-1", "policy-pay",
     "Salary bands and grade thresholds (restricted)."),
    ("pay-2", "policy-pay",
     "Leave is paid at the employee's base rate."),
]
con.executemany("INSERT INTO chunks VALUES (?,?,?)", rows)
con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
con.executemany(
    "INSERT INTO document_acl VALUES (?,?)",
    [("policy-leave", "all-staff"), ("wiki-forms", "all-staff"),
     ("policy-pay", "hr"), ("policy-pay", "management")])


def search(query: str, groups: list, k: int = 5):
    placeholders = ",".join("?" * len(groups))
    sql = f"""
      SELECT c.id, bm25(chunks_fts) AS score
      FROM chunks_fts f JOIN chunks c ON c.rowid = f.rowid
      WHERE chunks_fts MATCH ?
        AND EXISTS (SELECT 1 FROM document_acl a
                    WHERE a.document_id = c.document_id
                      AND a.group_id IN ({placeholders}))
      ORDER BY score LIMIT ?"""
    return con.execute(sql, [query, *groups, k]).fetchall()


print("staff:", search("leave OR salary", ["all-staff"]))
print("hr:   ", search("leave OR salary", ["all-staff", "hr"]))
