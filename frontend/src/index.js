import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Mount the App component inside the HTML #root element using React 18 rendering API.
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
