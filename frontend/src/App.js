import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './styles/App.css';
import NavBar from './components/NavBar';
import Footer from './components/Footer';
import ChatBot from './components/ChatBot';

// Components
import Dashboard from './components/Dashboard';
import Analysis from './components/Analysis';
import RatesTable from './components/RatesTable';
import AddRate from './components/AddRate';
import AdminPanel from './components/AdminPanel';

function App() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch from the analyze endpoint which provides summary data
    fetch('http://localhost:5000/api/analyze')
      .then(res => res.json())
      .then(data => {
        setSummary(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching summary:', err);
        setLoading(false);
      });
  }, []);

  return (
    <Router>
      <div className="App">
        <NavBar />
        <div className="main-content">
          {!loading && summary && (
            <div className="summary-bar">
              <div className="summary-item">
                <span>Average Rate</span>
                <strong>{summary.avg_rate?.toFixed(2)}%</strong>
              </div>
              <div className="summary-item">
                <span>Best Rate</span>
                <strong>{summary.max_rate?.toFixed(2)}%</strong>
              </div>
              <div className="summary-item">
                <span>Best Bank</span>
                <strong>{summary.best_bank}</strong>
              </div>
            </div>
          )}
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/rates" element={<RatesTable />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/analysis/:term" element={<Analysis />} />
          </Routes>
        </div>
        <Footer />
        <ChatBot />
      </div>
    </Router>
  );
}

export default App; 