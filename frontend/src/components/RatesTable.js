import React, { useState, useEffect } from 'react';
import '../styles/RatesTable.css';

function RatesTable() {
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(false);
  const [sortConfig, setSortConfig] = useState({
    key: 'regular_rate',
    direction: 'desc'
  });
  const [filters, setFilters] = useState({
    bank: '',
    minRate: '',
    maxRate: '',
    tenure: ''
  });

  useEffect(() => {
    fetch('http://localhost:5000/api/fd-rates')
      .then(res => res.json())
      .then(data => {
        if (data.rates) {
          setRates(data.rates);
        } else {
          setRates([]);
          console.error('No rates found in API response');
          setApiError(true);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching rates:', err);
        setApiError(true);
        setLoading(false);
      });
  }, []);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const filteredAndSortedRates = () => {
    if (!rates || rates.length === 0) {
      return [];
    }

    // Filter out implausible rates
    let result = rates.filter(rate => 
      rate.regular_rate && 
      !isNaN(parseFloat(rate.regular_rate)) && 
      parseFloat(rate.regular_rate) >= 1
    );

    // Apply user filters
    if (filters.bank) {
      result = result.filter(rate => 
        rate.bank && rate.bank.toLowerCase().includes(filters.bank.toLowerCase())
      );
    }
    if (filters.minRate) {
      result = result.filter(rate => 
        rate.regular_rate >= parseFloat(filters.minRate)
      );
    }
    if (filters.maxRate) {
      result = result.filter(rate => 
        rate.regular_rate <= parseFloat(filters.maxRate)
      );
    }
    if (filters.tenure) {
      result = result.filter(rate => 
        rate.tenure_description && rate.tenure_description.toLowerCase().includes(filters.tenure.toLowerCase())
      );
    }

    // Apply sorting
    result.sort((a, b) => {
      // Handle null or undefined values
      const aValue = a[sortConfig.key] !== undefined && a[sortConfig.key] !== null ? a[sortConfig.key] : -Infinity;
      const bValue = b[sortConfig.key] !== undefined && b[sortConfig.key] !== null ? b[sortConfig.key] : -Infinity;
      
      if (aValue < bValue) {
        return sortConfig.direction === 'asc' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortConfig.direction === 'asc' ? 1 : -1;
      }
      return 0;
    });

    return result;
  };

  if (loading) {
    return <div className="loading">Loading rates data...</div>;
  }

  return (
    <div className="rates-table-container">
      <h1>Fixed Deposit Rates</h1>

      {apiError && (
        <div className="api-error-banner">
          There was an error fetching the rates data. Some information may be missing or outdated.
        </div>
      )}

      <div className="filters">
        <div className="filter-group">
          <input
            type="text"
            name="bank"
            placeholder="Filter by bank..."
            value={filters.bank}
            onChange={handleFilterChange}
          />
        </div>
        <div className="filter-group">
          <input
            type="number"
            name="minRate"
            placeholder="Min rate..."
            value={filters.minRate}
            onChange={handleFilterChange}
          />
        </div>
        <div className="filter-group">
          <input
            type="number"
            name="maxRate"
            placeholder="Max rate..."
            value={filters.maxRate}
            onChange={handleFilterChange}
          />
        </div>
        <div className="filter-group">
          <input
            type="text"
            name="tenure"
            placeholder="Filter by tenure..."
            value={filters.tenure}
            onChange={handleFilterChange}
          />
        </div>
      </div>

      <div className="table-wrapper">
        <table className="rates-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('bank')}>
                Bank
                {sortConfig.key === 'bank' && (
                  <span>{sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('regular_rate')}>
                Regular Rate
                {sortConfig.key === 'regular_rate' && (
                  <span>{sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('senior_rate')}>
                Senior Rate
                {sortConfig.key === 'senior_rate' && (
                  <span>{sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('min_days')}>
                Tenure
                {sortConfig.key === 'min_days' && (
                  <span>{sortConfig.direction === 'asc' ? ' ↑' : ' ↓'}</span>
                )}
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedRates().length > 0 ? (
              filteredAndSortedRates().map((rate, index) => (
                <tr key={index}>
                  <td>{rate.bank || 'N/A'}</td>
                  <td>{rate.regular_rate ? rate.regular_rate.toFixed(2) : 'N/A'}%</td>
                  <td>{rate.senior_rate ? `${rate.senior_rate.toFixed(2)}%` : 'N/A'}</td>
                  <td>{rate.tenure_description || `${rate.min_days} days`}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="no-data">No rates match your filters</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RatesTable; 