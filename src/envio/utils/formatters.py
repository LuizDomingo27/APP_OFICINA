"""Funções de formatação para exibição."""

def fmt_number(value: float) -> str:
    """Formata número inteiro no padrão brasileiro (1.234.567)."""
    return f"{value:,.0f}".replace(",", ".")
