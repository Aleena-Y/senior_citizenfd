import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/NavBar.css';

function NavBar() {
  return (
    <nav className="navbar">
      <div className="nav-brand">FD Rate Analyzer</div>
      <div className="nav-links">
        <Link to="/">Dashboard</Link>
        <Link to="/analysis">Analysis</Link>
        <Link to="/rates">All Rates</Link>
      </div>
    </nav>
  );
}

export default NavBar; 