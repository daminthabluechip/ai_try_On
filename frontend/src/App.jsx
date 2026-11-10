// TODO: To add a new page, create it in src/pages/ and add a <Route> below.

import { Routes, Route } from 'react-router-dom'

import Navbar from './components/Navbar.jsx'
import HomePage from './pages/HomePage.jsx'
import CatalogPage from './pages/CatalogPage.jsx'
import TryOnPage from './pages/TryOnPage.jsx'
import ManageProductsPage from './pages/ManageProductsPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/try-on" element={<TryOnPage />} />
          <Route path="/manage" element={<ManageProductsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>

    </div>
  )
}

export default App
