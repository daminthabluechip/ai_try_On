// =====================================================================
// ErrorMessage.jsx  —  a red box that explains what went wrong.
// =====================================================================
//   message   -> the error text (if empty, nothing is shown)
//   onDismiss -> optional function; if given, an "×" close button appears

function ErrorMessage({ message, onDismiss }) {
  if (!message) {
    return null
  }

  return (
    // role="alert" makes screen readers announce the error immediately.
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
