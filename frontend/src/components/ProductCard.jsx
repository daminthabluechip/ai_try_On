function ProductCard({ product, buttonLabel, onButtonClick, isSelected = false }) {
  // TODO: Change 'USD' to your currency (e.g. 'LKR', 'EUR') and 'en-US' to your locale.
  const formattedPrice = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(product.price)

  let cardBorder = 'border-stone-200 hover:border-stone-300'
  if (isSelected) {
    cardBorder = 'border-brand ring-2 ring-brand'
  }

  return (
    <article
      className={`flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm transition ${cardBorder}`}
    >
      <div className="aspect-[4/5] bg-stone-100">
        {product.image_available ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center p-4 text-center text-xs text-muted">
            <span className="mb-1 text-3xl">👕</span>
            Image missing
            <br />
            (add backend/static/products/{product.image})
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <p className="text-xs font-medium tracking-wide text-muted uppercase">{product.category}</p>
        <h3 className="mt-1 font-display text-lg font-semibold">{product.name}</h3>
        <p className="mt-1 text-sm font-medium text-brand-dark">{formattedPrice}</p>

        <div className="mt-auto pt-4">
          <button
            type="button"
            onClick={() => onButtonClick(product)}
            className={`w-full rounded-full px-4 py-2 text-sm font-medium transition-colors ${
              isSelected
                ? 'bg-brand text-white'
                : 'border border-ink text-ink hover:bg-ink hover:text-white'
            }`}
          >
            {isSelected ? 'Selected ✓' : buttonLabel}
          </button>
        </div>
      </div>
    </article>
  )
}

export default ProductCard
