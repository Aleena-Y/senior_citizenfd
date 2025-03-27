import sqlite3
from datetime import datetime

def insert_initial_data():
    conn = sqlite3.connect('fd_rates.db')
    c = conn.cursor()
    
    # Sample data
    initial_data = [
        ('State Bank of India', '1 Year', 6.5, 1000, 1000000, 'India', 'INR', 0, 0),
        ('HDFC Bank', '1 Year', 6.75, 5000, 1000000, 'India', 'INR', 0, 0),
        ('ICICI Bank', '1 Year', 6.6, 10000, 1000000, 'India', 'INR', 0, 0),
        ('Axis Bank', '1 Year', 6.7, 5000, 1000000, 'India', 'INR', 0, 0),
        ('Kotak Mahindra Bank', '1 Year', 6.8, 5000, 1000000, 'India', 'INR', 0, 0)
    ]
    
    # Insert data
    c.executemany('''
        INSERT OR REPLACE INTO fd_rates 
        (bank_name, tenure, rate, min_amount, max_amount, region, currency, is_tax_saving, is_special_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', initial_data)
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    insert_initial_data()
    print("Initial data inserted successfully!") 