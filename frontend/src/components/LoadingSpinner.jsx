function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-3 py-10 text-muted">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-stone-200 border-t-brand" />
      <p className="text-sm">{message}</p>
    </div>
  )
}

export default LoadingSpinner
