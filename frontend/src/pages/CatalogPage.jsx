import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getProducts } from '../services/api.js'
import ProductCard from '../components/ProductCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

const ALL_CATEGORIES = 'All'

function CatalogPage() {
  const [products, setProducts] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [activeCategory, setActiveCategory] = useState(ALL_CATEGORIES)

  const navigate = useNavigate()

  useEffect(() => {
    async function loadProducts() {
      try {
        const loadedProducts = await getProducts()
        setProducts(loadedProducts)
      } catch (error) {
        setErrorMessage(error.message)
      } finally {
        setIsLoading(false)
      }
    }
    loadProducts()
  }, [])

  const categories = [ALL_CATEGORIES]
  for (const product of products) {
    if (!categories.includes(product.category)) {
      categories.push(product.category)
    }
  }

  let visibleProducts = products
  if (activeCategory !== ALL_CATEGORIES) {
    visibleProducts = products.filter((product) => product.category === activeCategory)
  }

  function goToTryOn(product) {
    navigate(`/try-on?product=${product.id}`)
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      {/* TODO: Change the catalog title and subtitle here. */}
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">Our Collection</h1>
      <p className="mt-2 text-muted">Choose any item and see how it looks on you.</p>

      <div className="mt-6 flex flex-wrap gap-2">
        {categories.map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => setActiveCategory(category)}
            className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
              category === activeCategory
                ? 'bg-ink text-white'
                : 'border border-stone-300 bg-white text-ink hover:border-ink'
            }`}
          >
            {category}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {isLoading && <LoadingSpinner message="Loading products..." />}

        <ErrorMessage message={errorMessage} />

        {!isLoading && !errorMessage && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 lg:gap-6">
            {visibleProducts.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                buttonLabel="Try On"
                onButtonClick={goToTryOn}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default CatalogPage
