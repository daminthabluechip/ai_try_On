// =====================================================================
// main.jsx  —  the very first JavaScript file that runs.
// =====================================================================
// It finds <div id="root"> in index.html and tells React to draw
// our <App /> inside it. You will rarely need to change this file.

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// BrowserRouter lets the app have several "pages" (/, /catalog, /try-on)
// while really being one single web page.
import { BrowserRouter } from 'react-router-dom'

import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  // StrictMode shows extra warnings in development to help find bugs.
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
