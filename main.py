from fastmcp import FastMCP
import sqlite3
import os
import sys
from datetime import datetime

# -------------------------------------------------
# FIXED DATABASE PATH (CRITICAL)
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "remote-server_db.db")

# -------------------------------------------------
# MCP SERVER
# -------------------------------------------------
mcp = FastMCP(name="Expense-server-2.o")

# -------------------------------------------------
# DATABASE INITIALIZATION
# -------------------------------------------------
def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            sub_category TEXT,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

    print(f"[INIT] Database initialized at {db_path}", file=sys.stderr)

init_db()

# -------------------------------------------------
# ADD EXPENSE
# -------------------------------------------------
@mcp.tool()
def add_expense(
    amount: float,
    category: str,
    date: str,
    sub_category: str = ""
) -> dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO expenses (amount, category, sub_category, date, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (amount, category, sub_category, date, datetime.utcnow().isoformat())
    )

    conn.commit()
    expense_id = cursor.lastrowid
    conn.close()

    print(f"[ADD] id={expense_id} amount={amount}", file=sys.stderr)

    return {
        "status": "success",
        "action": "add",
        "expense_id": expense_id,
        "amount": amount,
        "category": category,
        "sub_category": sub_category,
        "date": date
    }

# -------------------------------------------------
# LIST EXPENSES
# -------------------------------------------------
@mcp.tool()
def listing_expenses() -> dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, amount, category, sub_category, date, created_at
        FROM expenses
        ORDER BY date DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    print(f"[LIST] {len(rows)} expenses fetched", file=sys.stderr)

    return {
        "status": "success",
        "action": "list",
        "count": len(rows),
        "expenses": [
            {
                "id": r[0],
                "amount": r[1],
                "category": r[2],
                "sub_category": r[3],
                "date": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]
    }

# -------------------------------------------------
# UPDATE EXPENSE
# -------------------------------------------------
@mcp.tool()
def update_expense(
    expense_id: int,
    amount: float | None = None,
    category: str | None = None,
    sub_category: str | None = None,
    date: str | None = None
) -> dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    if cursor.fetchone() is None:
        conn.close()
        return {
            "status": "error",
            "action": "update",
            "message": f"Expense {expense_id} not found"
        }

    fields = []
    values = []

    if amount is not None:
        fields.append("amount = ?")
        values.append(amount)
    if category is not None:
        fields.append("category = ?")
        values.append(category)
    if sub_category is not None:
        fields.append("sub_category = ?")
        values.append(sub_category)
    if date is not None:
        fields.append("date = ?")
        values.append(date)

    if not fields:
        conn.close()
        return {
            "status": "error",
            "action": "update",
            "message": "No fields provided to update"
        }

    values.append(expense_id)
    query = f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?"

    cursor.execute(query, values)
    conn.commit()
    conn.close()

    print(f"[UPDATE] id={expense_id}", file=sys.stderr)

    return {
        "status": "success",
        "action": "update",
        "expense_id": expense_id,
        "updated_fields": fields
    }

# -------------------------------------------------
# DELETE EXPENSE
# -------------------------------------------------
@mcp.tool()
def delete_expense(expense_id: int) -> dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    if cursor.fetchone() is None:
        conn.close()
        return {
            "status": "error",
            "action": "delete",
            "message": f"Expense {expense_id} not found"
        }

    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

    print(f"[DELETE] id={expense_id}", file=sys.stderr)

    return {
        "status": "success",
        "action": "delete",
        "expense_id": expense_id,
        "message": "Expense deleted successfully"
    }

# -------------------------------------------------
# SUMMARIZE EXPENSES
# -------------------------------------------------
@mcp.tool()
def summarizing_expenses(start_date: str, end_date: str) -> dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT SUM(amount)
        FROM expenses
        WHERE date BETWEEN ? AND ?
        """,
        (start_date, end_date)
    )

    total = cursor.fetchone()[0] or 0.0
    conn.close()

    print(f"[SUMMARY] {start_date} → {end_date} = {total}", file=sys.stderr)

    return {
        "status": "success",
        "action": "summary",
        "start_date": start_date,
        "end_date": end_date,
        "total_expense": total
    }

# -------------------------------------------------
# SERVER START
# -------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport='http', host='0.0.0.0', port=8000)
