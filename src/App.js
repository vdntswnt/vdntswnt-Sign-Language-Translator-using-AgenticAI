// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import ISLConvert from './Pages/ISLConvert';

function App() {
  return (
    <Router>
      <Routes>
        <Route path='*' element={<ISLConvert />} />
      </Routes>
    </Router>
  );
}

export default App;