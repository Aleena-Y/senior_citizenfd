import React, { useState } from 'react';
import '../styles/AddRate.css';

function AddRate() {
  const [formData, setFormData] = useState({
    bank: '',
    tenure_description: '',
    min_days: 0,
    max_days: 0,
    regular_rate: 0,
    senior_rate: null,
    category: 'General'
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : Number(value)) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      // Validate form data
      const requiredFields = ['bank', 'tenure_description', 'min_days', 'max_days', 'regular_rate'];
      const missingFields = requiredFields.filter(field => !formData[field]);
      
      if (missingFields.length > 0) {
        throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
      }

      // Send data to API
      const response = await fetch('http://localhost:5000/api/add-rate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to add rate');
      }

      setMessage(data.message || 'Rate added successfully');
      
      // Reset form
      setFormData({
        bank: '',
        tenure_description: '',
        min_days: 0,
        max_days: 0,
        regular_rate: 0,
        senior_rate: null,
        category: 'General'
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="add-rate-container">
      <h1>Add New FD Rate</h1>
      
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit} className="add-rate-form">
        <div className="form-group">
          <label htmlFor="bank">Bank Name*</label>
          <input
            type="text"
            id="bank"
            name="bank"
            value={formData.bank}
            onChange={handleChange}
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="tenure_description">Tenure Description*</label>
          <input
            type="text"
            id="tenure_description"
            name="tenure_description"
            value={formData.tenure_description}
            onChange={handleChange}
            placeholder="e.g. 1 year to 2 years"
            required
          />
        </div>
        
        <div className="form-row">
          <div className="form-group half">
            <label htmlFor="min_days">Minimum Days*</label>
            <input
              type="number"
              id="min_days"
              name="min_days"
              value={formData.min_days}
              onChange={handleChange}
              min="1"
              required
            />
          </div>
          
          <div className="form-group half">
            <label htmlFor="max_days">Maximum Days*</label>
            <input
              type="number"
              id="max_days"
              name="max_days"
              value={formData.max_days}
              onChange={handleChange}
              min="1"
              required
            />
          </div>
        </div>
        
        <div className="form-row">
          <div className="form-group half">
            <label htmlFor="regular_rate">Regular Rate (%)*</label>
            <input
              type="number"
              id="regular_rate"
              name="regular_rate"
              value={formData.regular_rate}
              onChange={handleChange}
              step="0.01"
              min="0"
              required
            />
          </div>
          
          <div className="form-group half">
            <label htmlFor="senior_rate">Senior Rate (%)</label>
            <input
              type="number"
              id="senior_rate"
              name="senior_rate"
              value={formData.senior_rate || ''}
              onChange={handleChange}
              step="0.01"
              min="0"
              placeholder="Optional"
            />
          </div>
        </div>
        
        <div className="form-group">
          <label htmlFor="category">Category</label>
          <select
            id="category"
            name="category"
            value={formData.category}
            onChange={handleChange}
          >
            <option value="General">General</option>
            <option value="Special">Special</option>
            <option value="Tax Saving">Tax Saving</option>
            <option value="NRI">NRI</option>
          </select>
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Adding...' : 'Add Rate'}
        </button>
      </form>
      
      <div className="import-csv-section">
        <h2>Import from CSV</h2>
        <p>You can also import FD rates from a CSV file. The CSV should have columns: bank, tenure_description, min_days, max_days, regular_rate, senior_rate (optional), category (optional).</p>
        {/* CSV import functionality would be added here in a real application */}
      </div>
    </div>
  );
}

export default AddRate; 