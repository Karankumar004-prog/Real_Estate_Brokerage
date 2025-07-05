from cryptography.fernet import Fernet
import pandas as pd

def generate_encryption_key():
    return Fernet.generate_key()

def export_to_csv(queryset, output):
    rows = []
    for item in queryset:
        rows.append({
            'Date': item.created_at.strftime('%Y-%m-%d') if item.created_at else '',
            'Name': item.name,
            'Phone': item.phone,
            'Budget': format_budget(item.budget),
            'Area': item.area,
            'Preferred Building': item.preferred_building,
            'Status': item.status
        })
    df = pd.DataFrame(rows)
    df.to_csv(output, index=False)

def format_budget(amount):
    try:
        amount = float(amount)
        if amount >= 1e7:
            return f"{amount/1e7:.2f}Cr"
        elif amount >= 1e5:
            return f"{amount/1e5:.2f}L"
        else:
            return str(int(amount))
    except Exception:
        return str(amount) 