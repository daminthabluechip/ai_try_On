import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <h1 className="font-display text-4xl font-semibold">Page not found</h1>
      <p className="mt-3 text-muted">The page you are looking for doesn't exist.</p>
      <Link to="/" className="mt-8 inline-block rounded-full bg-brand px-6 py-2.5 text-white hover:bg-brand-dark">
        Back to Home
      </Link>
    </div>
  )
}

export default NotFoundPage
