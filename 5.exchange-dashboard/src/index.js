import React from 'react';
import ReactDOM from 'react-dom';
import './index.css'; // Ensure this file exists, or remove this line.
import App from './App'; // Ensure App.js exists in the same folder.

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root') // Matches the `id="root"` in public/index.html.
);