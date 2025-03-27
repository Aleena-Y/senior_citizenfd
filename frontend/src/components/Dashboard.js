import React, { useState, useEffect } from 'react';
import '../styles/Dashboard.css';

function Dashboard() {
  const [topBanks, setTopBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [fdRates, setFdRates] = useState([]);
  const [apiError, setApiError] = useState(false);

  useEffect(() => {
    // Fetch top banks
    fetch('http://localhost:5000/api/top-banks')
      .then(res => res.json())
      .then(data => {
        if (data.top_banks) {
          setTopBanks(data.top_banks);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching top banks:', err);
        setApiError(true);
        setLoading(false);
      });
    
    // Fetch summary data
    fetch('http://localhost:5000/api/analyze')
      .then(res => res.json())
      .then(data => {
        setSummary(data);
      })
      .catch(err => {
        console.error('Error fetching summary:', err);
        setApiError(true);
      });

    // Fetch all FD rates
    fetch('http://localhost:5000/api/fd-rates')
      .then(res => res.json())
      .then(data => {
        if (data.rates) {
          setFdRates(data.rates);
        }
      })
      .catch(err => {
        console.error('Error fetching FD rates:', err);
        setApiError(true);
      });
  }, []);

  const getTermAnalysis = (term) => {
    if (!fdRates || !fdRates.length) return null;

    // Filter out invalid data
    const validRates = fdRates.filter(rate => 
      rate.regular_rate && !isNaN(parseFloat(rate.regular_rate)) && 
      parseFloat(rate.regular_rate) >= 1
    );

    if (!validRates.length) return null;

    let filteredRates;
    switch(term) {
      case 'short':
        filteredRates = validRates.filter(rate => rate.min_days <= 365);
        break;
      case 'medium':
        filteredRates = validRates.filter(rate => rate.min_days > 365 && rate.min_days <= 1095);
        break;
      case 'long':
        filteredRates = validRates.filter(rate => rate.min_days > 1095);
        break;
      default:
        filteredRates = [];
    }

    if (!filteredRates.length) return null;

    const avgRate = filteredRates.reduce((sum, rate) => sum + parseFloat(rate.regular_rate), 0) / filteredRates.length;
    const maxRate = Math.max(...filteredRates.map(rate => parseFloat(rate.regular_rate)));
    const bestBank = filteredRates.find(rate => parseFloat(rate.regular_rate) === maxRate)?.bank;

    return {
      avgRate: avgRate.toFixed(2),
      maxRate: maxRate.toFixed(2),
      bestBank
    };
  };

  if (loading) {
    return <div className="loading">Loading dashboard data...</div>;
  }

  return (
    <div className="dashboard">
      <h1>FD Rates Dashboard</h1>
      
      {apiError && (
        <div className="api-error-banner">
          There was an error fetching some data. Showing available information.
        </div>
      )}

      <section className="top-banks">
        <h2>Top Banks by Interest Rate</h2>
        <div className="bank-cards">
          {topBanks.map((bank, index) => (
            <div key={index} className="bank-card">
              <h3>{bank.bank}</h3>
              <div className="rate-info">
                <div className="max-rate">
                  <span>Rate</span>
                  <strong>{bank.regular_rate.toFixed(2)}%</strong>
                </div>
                <div className="tenure">
                  <span>Tenure</span>
                  <strong>{bank.tenure_description}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {summary && (
        <section className="market-summary">
          <h2>Market Overview</h2>
          <div className="summary-stats">
            <div className="stat-card">
              <h3>Average Rate</h3>
              <div className="stat-value">{summary.avg_rate.toFixed(2)}%</div>
            </div>
            <div className="stat-card">
              <h3>Best Rate</h3>
              <div className="stat-value">{summary.max_rate.toFixed(2)}%</div>
              <div className="stat-detail">from {summary.best_bank}</div>
            </div>
          </div>
        </section>
      )}

      <section className="quick-analysis">
        <h2>Quick Analysis</h2>
        <div className="analysis-grid">
          <div className="analysis-card">
            <h3>Short Term (up to 1 year)</h3>
            {getTermAnalysis('short') ? (
              <>
                <p>Average Rate: {getTermAnalysis('short').avgRate}%</p>
                <p>Best Rate: {getTermAnalysis('short').maxRate}% from {getTermAnalysis('short').bestBank}</p>
              </>
            ) : (
              <p>Best for emergency funds and short-term goals</p>
            )}
            <button onClick={() => window.location.href = '/analysis?term=short'}>
              Analyze Short Term FDs
            </button>
          </div>
          <div className="analysis-card">
            <h3>Medium Term (1-3 years)</h3>
            {getTermAnalysis('medium') ? (
              <>
                <p>Average Rate: {getTermAnalysis('medium').avgRate}%</p>
                <p>Best Rate: {getTermAnalysis('medium').maxRate}% from {getTermAnalysis('medium').bestBank}</p>
              </>
            ) : (
              <p>Balanced returns with moderate liquidity</p>
            )}
            <button onClick={() => window.location.href = '/analysis?term=medium'}>
              Analyze Medium Term FDs
            </button>
          </div>
          <div className="analysis-card">
            <h3>Long Term (over 3 years)</h3>
            {getTermAnalysis('long') ? (
              <>
                <p>Average Rate: {getTermAnalysis('long').avgRate}%</p>
                <p>Best Rate: {getTermAnalysis('long').maxRate}% from {getTermAnalysis('long').bestBank}</p>
              </>
            ) : (
              <p>Maximum returns for long-term savings</p>
            )}
            <button onClick={() => window.location.href = '/analysis?term=long'}>
              Analyze Long Term FDs
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Dashboard; 