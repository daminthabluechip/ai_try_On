function ErrorMessage({ message, onDismiss }) {
  if (!message) {
    return null
  }

  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <p>
        <span className="font-semibold">Error: </span>
        {message}
      </p>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Close error message"
          className="text-lg leading-none text-red-600 hover:text-red-900"
        >
          ×
        </button>
      )}
    </div>
  )
}

export default ErrorMessage
