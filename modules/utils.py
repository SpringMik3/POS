def format_currency(amount):
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0
    return f"{value:,.0f} ₫"

def format_datetime(dt):
    return dt.strftime('%d/%m/%Y %H:%M')
