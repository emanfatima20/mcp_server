from fastmcp import FastMCP
import aiosqlite
import os
import sys
from datetime import datetime, date

# -------------------------------------------------
# MCP SERVER
# -------------------------------------------------
mcp = FastMCP(name="expense-mcp-async")

# -------------------------------------------------
# DATABASE PATH (PERSISTENT)
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

# -------------------------------------------------
# INIT DATABASE (ASYNC)
# -------------------------------------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                sub_category TEXT DEFAULT '',
                expense_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()

    print(f"[INIT] DB initialized at {DB_PATH}", file=sys.stderr)

# Run once at startup
import asyncio
asyncio.run(init_db())

# -------------------------------------------------
# ADD EXPENSE
# -------------------------------------------------
@mcp.tool()
async def add_expense(
    amount: float,
    category: str,
    expense_date: str | None = None,
    sub_category: str = ""
) -> dict:
    if expense_date is None:
        expense_date = date.today().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO expenses (amount, category, sub_category, expense_date, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            amount,
            category.lower(),
            sub_category.lower(),
            expense_date,
            datetime.utcnow().isoformat()
        ))
        await db.commit()
        expense_id = cursor.lastrowid

    return {
        "status": "success",
        "expense_id": expense_id,
        "amount": amount,
        "category": category,
        "sub_category": sub_category,
        "date": expense_date
    }

# -------------------------------------------------
# LIST EXPENSES
# -------------------------------------------------
@mcp.tool()
async def list_expenses() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, amount, category, sub_category, expense_date, created_at
            FROM expenses
            ORDER BY expense_date DESC
        """)
        rows = await cursor.fetchall()

    return {
        "count": len(rows),
        "expenses": [
            {
                "id": r[0],
                "amount": r[1],
                "category": r[2],
                "sub_category": r[3],
                "date": r[4],
                "created_at": r[5]
            }
            for r in rows
        ]
    }

# -------------------------------------------------
# UPDATE EXPENSE
# -------------------------------------------------
@mcp.tool()
async def update_expense(
    expense_id: int,
    amount: float | None = None,
    category: str | None = None,
    sub_category: str | None = None,
    expense_date: str | None = None
) -> dict:

    fields = []
    values = []

    if amount is not None:
        fields.append("amount = ?")
        values.append(amount)
    if category is not None:
        fields.append("category = ?")
        values.append(category.lower())
    if sub_category is not None:
        fields.append("sub_category = ?")
        values.append(sub_category.lower())
    if expense_date is not None:
        fields.append("expense_date = ?")
        values.append(expense_date)

    if not fields:
        return {"status": "error", "message": "No fields to update"}

    values.append(expense_id)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?",
            values
        )
        await db.commit()

    return {"status": "success", "updated_fields": fields}

# -------------------------------------------------
# DELETE EXPENSE
# -------------------------------------------------
@mcp.tool()
async def delete_expense(expense_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        await db.commit()

    return {"status": "success", "deleted_id": expense_id}

# -------------------------------------------------
# SUMMARY
# -------------------------------------------------
@mcp.tool()
async def summarize_expenses(start_date: str, end_date: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT SUM(amount)
            FROM expenses
            WHERE expense_date BETWEEN ? AND ?
        """, (start_date, end_date))
        total = (await cursor.fetchone())[0] or 0.0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_expense": total
    }

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )
