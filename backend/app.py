from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from datetime import datetime
import os
from models import FDRate, get_db, engine, Base
from sqlalchemy.orm import Session
from sqlalchemy import func
from config import DB_CONFIG

app = Flask(__name__)
CORS(app)

def import_latest_csv_to_db():
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Get the latest CSV file
    data_dir = 'data'
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    if not csv_files:
        print("No CSV files found in data directory")
        return False
    
    latest_file = max(csv_files, key=lambda x: os.path.getctime(os.path.join(data_dir, x)))
    print(f"Importing data from {latest_file}")
    
    # Read CSV file
    df = pd.read_csv(os.path.join(data_dir, latest_file))
    
    # Create database session
    Session = Session(bind=engine)
    session = Session()
    
    try:
        # Convert DataFrame to list of dictionaries
        records = df.to_dict('records')
        
        # Insert or update records
        for record in records:
            # Create FDRate instance
            fd_rate = FDRate(
                bank=record['bank'],
                tenure_description=record['tenure_description'],
                min_days=record['min_days'],
                max_days=record['max_days'],
                regular_rate=record['regular_rate'],
                senior_rate=record['senior_rate'],
                category=record['category'],
                region=record.get('region'),
                currency=record.get('currency'),
                is_tax_saving=record.get('is_tax_saving', False),
                is_special_rate=record.get('is_special_rate', False)
            )
            
            # Merge (insert or update) the record
            session.merge(fd_rate)
        
        # Commit the changes
        session.commit()
        print(f"Successfully imported {len(records)} records")
        return True
        
    except Exception as e:
        print(f"Error importing data: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close()

@app.route('/api/fd-rates', methods=['GET'])
def get_fd_rates():
    try:
        db = next(get_db())
        try:
            # Get query parameters
            bank = request.args.get('bank')
            min_days = request.args.get('min_days')
            max_days = request.args.get('max_days')
            min_rate = request.args.get('min_rate')
            max_rate = request.args.get('max_rate')
            
            # Build the query
            query = db.query(FDRate)
            
            if bank:
                query = query.filter(FDRate.bank == bank)
            if min_days:
                query = query.filter(FDRate.min_days >= int(min_days))
            if max_days:
                query = query.filter(FDRate.max_days <= int(max_days))
            if min_rate:
                query = query.filter(FDRate.regular_rate >= float(min_rate))
            if max_rate:
                query = query.filter(FDRate.regular_rate <= float(max_rate))
            
            rates = query.all()
            
            return jsonify([{
                'id': rate.id,
                'bank': rate.bank,
                'tenure_description': rate.tenure_description,
                'min_days': rate.min_days,
                'max_days': rate.max_days,
                'regular_rate': rate.regular_rate,
                'senior_rate': rate.senior_rate,
                'category': rate.category,
                'scraped_date': rate.scraped_date.strftime('%Y-%m-%d'),
                'region': rate.region,
                'currency': rate.currency,
                'is_tax_saving': rate.is_tax_saving,
                'is_special_rate': rate.is_special_rate
            } for rate in rates])
        finally:
            db.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        db = next(get_db())
        try:
            # Get all rates
            rates = db.query(FDRate).all()
            
            # Convert to DataFrame
            df = pd.DataFrame([{
                'bank': rate.bank,
                'tenure_description': rate.tenure_description,
                'min_days': rate.min_days,
                'max_days': rate.max_days,
                'regular_rate': rate.regular_rate,
                'senior_rate': rate.senior_rate,
                'category': rate.category
            } for rate in rates])
            
            # Filter based on risk preference
            if data.get('risk_preference') == 'low':
                df = df[df['max_days'] <= 365]
            elif data.get('risk_preference') == 'medium':
                df = df[(df['max_days'] > 365) & (df['max_days'] <= 1095)]
            else:  # high
                df = df[df['max_days'] > 1095]
            
            # Prepare features for clustering
            features = df[['regular_rate', 'max_days']].copy()
            features['max_days'] = features['max_days'] / 365  # Convert to years
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Perform clustering
            n_clusters = min(3, len(df))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            df['cluster'] = kmeans.fit_predict(features_scaled)
            
            # Get recommendations
            recommendations = []
            for cluster in range(n_clusters):
                cluster_data = df[df['cluster'] == cluster]
                top_rates = cluster_data.nlargest(3, 'regular_rate')
                recommendations.extend(top_rates.to_dict('records'))
            
            return jsonify({
                'recommendations': recommendations,
                'total_options': len(df),
                'clusters': n_clusters
            })
        finally:
            db.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/top-banks', methods=['GET'])
def top_banks():
    try:
        db = next(get_db())
        try:
            # Get top banks by average rate
            top_banks = db.query(
                FDRate.bank,
                func.avg(FDRate.regular_rate).label('avg_rate'),
                func.count(FDRate.id).label('num_products')
            ).group_by(FDRate.bank)\
             .order_by(func.avg(FDRate.regular_rate).desc())\
             .limit(10)\
             .all()
            
            return jsonify([{
                'bank': bank,
                'avg_rate': float(avg_rate),
                'num_products': num_products
            } for bank, avg_rate, num_products in top_banks])
        finally:
            db.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-scraper', methods=['POST'])
def run_scraper():
    try:
        # Import scraper at runtime to avoid circular imports
        from scraper import run_all_scrapers
        data = run_all_scrapers()
        
        if data:
            # Import the scraped data
            success = import_latest_csv_to_db()
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Successfully scraped and imported {len(data)} records',
                    'count': len(data)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to import scraped data'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'No data was scraped'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error running scraper: {str(e)}'
        }), 500

@app.route('/api/import-csv', methods=['POST'])
def import_csv():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
            
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "File must be a CSV"}), 400
            
        # Save the file temporarily
        temp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp.csv")
        file.save(temp_path)
        
        # Read and import the data
        df = pd.read_csv(temp_path)
        success = import_latest_csv_to_db()
        
        # Clean up
        os.remove(temp_path)
        
        if success:
            return jsonify({"message": "Data imported successfully"})
        else:
            return jsonify({"error": "Failed to import data"}), 500
            
    except Exception as e:
        print(f"Error importing CSV: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 