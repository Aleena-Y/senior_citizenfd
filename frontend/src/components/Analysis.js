import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import '../styles/Analysis.css';

function Analysis() {
  const location = useLocation();
  const searchParams = new URLSearchParams(location.search);
  const termFromUrl = searchParams.get('term');

  const [formData, setFormData] = useState({
    investment_amount: 100000,
    age: 30,
    risk_preference: termFromUrl === 'short' ? 'Conservative' : 
                     termFromUrl === 'medium' ? 'Moderate' : 
                     termFromUrl === 'long' ? 'Aggressive' : 'Moderate'
  });

  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fdRates, setFdRates] = useState([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [apiError, setApiError] = useState(false);

  // Fetch all FD rates once on component mount
  useEffect(() => {
    setDataLoading(true);
    console.log("Fetching FD rates data...");
    fetch('http://localhost:5000/api/fd-rates')
      .then(res => res.json())
      .then(data => {
        console.log("Received data:", data);
        if (data.rates) {
          setFdRates(data.rates);
          console.log(`Loaded ${data.rates.length} FD rates`);
          // Auto-analyze if term is provided in URL
          if (termFromUrl) {
            handleAnalysis(data.rates);
          }
        } else {
          console.error("No rates found in response:", data);
          setApiError(true);
        }
        setDataLoading(false);
      })
      .catch(err => {
        console.error('Error fetching FD rates:', err);
        setApiError(true);
        setDataLoading(false);
      });
  }, [termFromUrl]);

  const handleAnalysis = (rates = fdRates) => {
    console.log("Analyzing investment with data:", formData);
    setApiError(false);
    
    try {
      if (!rates || rates.length === 0) {
        console.error("No FD rates available for analysis");
        setApiError(true);
        return;
      }

      // Call the backend API with parameters for analysis
      const apiUrl = `http://localhost:5000/api/analyze?risk_preference=${formData.risk_preference.toLowerCase()}`;
      
      setLoading(true);
      fetch(apiUrl)
        .then(res => res.json())
        .then(data => {
          console.log("Analysis API response:", data);
          
          if (!data || !data.recommendations || data.recommendations.length === 0) {
            console.error("Invalid analysis response from API");
            setApiError(true);
            return;
          }
          
          // Calculate potential return based on best rate
          const potentialReturn = formData.investment_amount * (1 + data.max_rate/100);
          
          setAnalysis({
            average_rate: data.avg_rate.toFixed(2),
            best_rate: data.max_rate.toFixed(2),
            best_bank: data.best_bank,
            potential_return: potentialReturn,
            recommendations: data.recommendations
          });
        })
        .catch(err => {
          console.error('Error calling analysis API:', err);
          setApiError(true);
        })
        .finally(() => {
          setLoading(false);
        });
    } catch (error) {
      console.error('Error analyzing investment:', error);
      setApiError(true);
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleAnalysis();
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'investment_amount' || name === 'age' ? Number(value) : value
    }));
  };

  return (
    <div className="analysis-container">
      <h1>Investment Analysis</h1>
      
      {apiError && (
        <div className="api-error-banner">
          There was an error fetching or analyzing the data. Some information may be missing or outdated.
        </div>
      )}
      
      <div className="analysis-content">
        <div className="input-section">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="investment_amount">Investment Amount (₹)</label>
              <input
                type="number"
                id="investment_amount"
                name="investment_amount"
                value={formData.investment_amount}
                onChange={handleChange}
                min="1000"
                step="1000"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="age">Age</label>
              <input
                type="number"
                id="age"
                name="age"
                value={formData.age}
                onChange={handleChange}
                min="18"
                max="100"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="risk_preference">Risk Preference</label>
              <select
                id="risk_preference"
                name="risk_preference"
                value={formData.risk_preference}
                onChange={handleChange}
                required
              >
                <option value="Conservative">Conservative (up to 1 year)</option>
                <option value="Moderate">Moderate (1-3 years)</option>
                <option value="Aggressive">Aggressive (3+ years)</option>
              </select>
            </div>

            <button type="submit" disabled={loading || dataLoading}>
              {loading ? 'Analyzing...' : dataLoading ? 'Loading Data...' : 'Analyze Investment'}
            </button>
          </form>
        </div>

        {analysis && (
          <div className="results-section">
            <div className="results-summary">
              <div className="result-card">
                <h3>Average Market Rate</h3>
                <p className="rate">{analysis.average_rate}%</p>
              </div>
              <div className="result-card highlight">
                <h3>Best Available Rate</h3>
                <p className="rate">{analysis.best_rate}%</p>
                <p className="bank">from {analysis.best_bank}</p>
              </div>
              <div className="result-card">
                <h3>Potential Return</h3>
                <p className="amount">₹{analysis.potential_return.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</p>
              </div>
            </div>

            <div className="recommendations">
              <h2>Top Recommendations</h2>
              <div className="recommendations-grid">
                {analysis.recommendations.map((rec, index) => (
                  <div key={index} className="recommendation-card">
                    <h3>{rec.bank}</h3>
                    <div className="rec-details">
                      <p className="rec-rate">{parseFloat(rec.regular_rate).toFixed(2)}%</p>
                      <p className="rec-tenure">{rec.tenure_description || `${rec.min_days} days`}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Analysis; 