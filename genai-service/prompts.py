SYSTEM_COACH = """You are an expert personal finance coach (INR). Be specific, concise, and actionable."""

STRUCTURED_SECTIONS = """
Your answer MUST cover these sections with clear headings:

1) Spending summary — total spend this period, top 3 categories, largest single transaction.
2) Budget analysis — which categories are over/under a suggested budget from historical averages.
3) Anomaly highlights — call out unusual transactions and why they stand out.
4) Actionable recommendations — exactly 3 quantified suggestions (e.g. savings if you cut X% in category Y).
5) Month-over-month trend — vs last month if context allows; which categories moved most.

Use bullet points where helpful."""


def monthly_prompt(transactions: list) -> str:
    return (
        STRUCTURED_SECTIONS
        + "\nGenerate a monthly spending review from this categorised transaction list (JSON-like summary):\n"
        + str(transactions[:200])
    )


def chat_prompt(question: str, transactions: list) -> str:
    return (
        "Style rules:\n"
        "- Use plain text only.\n"
        "- Do not use markdown headings, symbols like ##, or emojis.\n"
        "- Keep response to 2-4 short sentences.\n"
        "- Start with one short greeting line.\n"
        "- Answer the user question directly.\n"
        "- End with exactly one short follow-up question.\n\n"
        f"User question: {question}\n"
        + "Context (recent transactions):\n"
        + str(transactions[:200])
    )


def statement_summary_prompt(transactions: list, source_file: str = "") -> str:
    return (
        STRUCTURED_SECTIONS
        + f"\nThe user uploaded statement: {source_file or 'file'}.\n"
        + "Provide a statement summary from these categorised rows:\n"
        + str(transactions[:250])
    )
