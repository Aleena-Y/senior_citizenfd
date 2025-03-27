import React, { useState, useEffect } from 'react';
import '../styles/AdminPanel.css';

function AdminPanel() {
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRate, setSelectedRate] = useState(null);
  const [message, setMessage] = useState(null);
  const [formData, setFormData] = useState({
    bank: '',
    tenure_description: '',
    min_days: '',
    max_days: '',
    regular_rate: '',
    senior_rate: '',
    category: 'General'
  });
  const [formMode, setFormMode] = useState('add'); // 'add' or 'edit'

  // Fetch rates on component mount
  useEffect(() => {
    fetchRates();
  }, []);

  const fetchRates = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/fd-rates');
      if (response.ok) {
        const data = await response.json();
        setRates(data.rates || []);
      } else {
        console.error('Failed to fetch rates');
      }
    } catch (error) {
      console.error('Error fetching rates:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    let updatedValue = value;
    
    // Convert numeric fields to numbers
    if (['min_days', 'max_days'].includes(name)) {
      updatedValue = value === '' ? '' : parseInt(value, 10);
    } else if (['regular_rate', 'senior_rate'].includes(name)) {
      updatedValue = value === '' ? '' : parseFloat(value);
    }
    
    setFormData({
      ...formData,
      [name]: updatedValue
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setError('');

    try {
      const response = await fetch('http://localhost:5000/api/add-rate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(data.message || 'Rate added successfully');
        // Reset form after successful submission
        setFormData({
          bank: '',
          tenure_description: '',
          min_days: '',
          max_days: '',
          regular_rate: '',
          senior_rate: '',
          category: 'General'
        });
        // Refresh rates list
        fetchRates();
      } else {
        setError(data.error || 'Failed to add rate');
      }
    } catch (error) {
      setError('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (rate) => {
    setSelectedRate(rate);
    setFormData({
      id: rate.id,
      bank: rate.bank,
      tenure_description: rate.tenure_description,
      min_days: rate.min_days,
      max_days: rate.max_days,
      regular_rate: rate.regular_rate,
      senior_rate: rate.senior_rate || null,
      category: rate.category || 'General'
    });
    setFormMode('edit');
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this rate?')) {
      return;
    }
    
    setMessage(null);
    setError(null);
    
    try {
      // In a real app, you would have a delete endpoint
      // For this example, we'll just log the deletion
      console.log(`Would delete rate with ID: ${id}`);
      
      // Show success message
      setMessage('Rate deleted successfully');
      
      // Refresh data - in a real app, this would be after successful API call
      fetchRates();
      
    } catch (err) {
      setError(err.message);
    }
  };

  const resetForm = () => {
    setFormData({
      bank: '',
      tenure_description: '',
      min_days: '',
      max_days: '',
      regular_rate: '',
      senior_rate: '',
      category: 'General'
    });
    setSelectedRate(null);
    setFormMode('add');
  };

  const runScraper = async () => {
    setLoading(true);
    setMessage('');
    setError('');
    
    try {
      const response = await fetch('http://localhost:5000/api/run-scraper', {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setMessage(`${data.message} The database has been ${data.database_updated ? 'successfully updated' : 'not updated'}.`);
        // Refresh rates after running scraper
        fetchRates();
      } else {
        setError(data.error || 'Failed to run scraper');
      }
    } catch (error) {
      setError('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const importLatestCSV = async () => {
    setLoading(true);
    setMessage('');
    setError('');
    
    try {
      const response = await fetch('http://localhost:5000/api/import-csv', {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setMessage(data.message || 'Latest CSV data successfully imported to database');
        // Refresh rates after importing
        fetchRates();
      } else {
        setError(data.error || 'Failed to import CSV data');
      }
    } catch (error) {
      setError('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRate = async (rateId) => {
    if (window.confirm('Are you sure you want to delete this rate?')) {
      try {
        const response = await fetch(`http://localhost:5000/api/delete-rate/${rateId}`, {
          method: 'DELETE',
        });
        
        if (response.ok) {
          // Refresh rates after deletion
          fetchRates();
          setMessage('Rate deleted successfully');
          setError('');
        } else {
          const errorData = await response.json();
          setError(`Failed to delete rate: ${errorData.error}`);
          setMessage('');
        }
      } catch (error) {
        setError(`Error deleting rate: ${error.message}`);
        setMessage('');
      }
    }
  };

  if (loading && rates.length === 0) {
    return <div className="admin-panel"><div className="loading">Loading rates...</div></div>;
  }

  return (
    <div className="admin-panel">
      <h1>Admin Panel</h1>
      
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
      
      <div className="admin-actions">
        <button 
          onClick={runScraper} 
          disabled={loading}
          className="run-scraper-btn"
        >
          {loading ? 'Running...' : 'Run Scraper & Update DB'}
        </button>
        
        <button 
          onClick={importLatestCSV}
          disabled={loading}
          className="import-btn"
        >
          {loading ? 'Importing...' : 'Import Latest CSV'}
        </button>
        
        <button 
          onClick={resetForm}
          className={formMode === 'add' ? 'hidden' : 'cancel-btn'}
        >
          Cancel Edit
        </button>
      </div>
      
      <div className="admin-layout">
        <div className="rate-form-panel">
          <h2>{formMode === 'add' ? 'Add New Rate' : 'Edit Rate'}</h2>
          
          <form onSubmit={handleSubmit} className="rate-form">
            <div className="form-group">
              <label htmlFor="bank">Bank Name*</label>
              <input
                type="text"
                id="bank"
                name="bank"
                value={formData.bank}
                onChange={handleInputChange}
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
                onChange={handleInputChange}
                required
                placeholder="e.g., 1 year to 2 years"
              />
            </div>
            
            <div className="form-row">
              <div className="form-group half">
                <label htmlFor="min_days">Min Days*</label>
                <input
                  type="number"
                  id="min_days"
                  name="min_days"
                  value={formData.min_days}
                  onChange={handleInputChange}
                  min="1"
                  required
                />
              </div>
              
              <div className="form-group half">
                <label htmlFor="max_days">Max Days*</label>
                <input
                  type="number"
                  id="max_days"
                  name="max_days"
                  value={formData.max_days}
                  onChange={handleInputChange}
                  min="1"
                  required
                />
              </div>
            </div>
            
            <div className="form-row">
              <div className="form-group half">
                <label htmlFor="regular_rate">Regular Rate (%)</label>
                <input
                  type="number"
                  id="regular_rate"
                  name="regular_rate"
                  value={formData.regular_rate}
                  onChange={handleInputChange}
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
                  value={formData.senior_rate}
                  onChange={handleInputChange}
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
                onChange={handleInputChange}
              >
                <option value="General">General</option>
                <option value="Special">Special</option>
                <option value="Tax Saving">Tax Saving</option>
                <option value="NRI">NRI</option>
              </select>
            </div>
            
            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Adding...' : 'Add Rate'}
            </button>
          </form>
        </div>
        
        <div className="rates-table-panel">
          <h2>Manage Rates</h2>
          
          {rates.length === 0 ? (
            <p>No rates found</p>
          ) : (
            <div className="table-container">
              <table className="rates-admin-table">
                <thead>
                  <tr>
                    <th>Bank</th>
                    <th>Tenure</th>
                    <th>Regular Rate</th>
                    <th>Senior Rate</th>
                    <th>Category</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rates.map(rate => (
                    <tr key={rate.id}>
                      <td>{rate.bank}</td>
                      <td>{rate.tenure_desc || rate.tenure_description}</td>
                      <td>{parseFloat(rate.regular_rate).toFixed(2)}%</td>
                      <td>{parseFloat(rate.senior_rate || 0).toFixed(2)}%</td>
                      <td>{rate.category || 'General'}</td>
                      <td className="action-buttons">
                        <button 
                          onClick={() => handleEdit(rate)}
                          className="edit-btn"
                        >
                          Edit
                        </button>
                        <button 
                          onClick={() => handleDeleteRate(rate.id)}
                          className="delete-btn"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminPanel; 