// =====================================================================
// LoadingSpinner.jsx  —  a spinning circle with a message.
// =====================================================================
// Shown while we wait for the backend (loading products, AI generation).
//   message -> the text shown under the spinner

function LoadingSpinner({ message = 'Loading...' }) {
  return (
    // role="status" tells screen readers that this area shows progress.
    <div role="status" className="flex flex-col items-center justify-center gap-3 py-10 text-muted">
      {/* A circle with one coloured side, rotated forever by "animate-spin" */}
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-stone-200 border-t-brand" />
      <p className="text-sm">{message}</p>
    </div>
  )
}

export default LoadingSpinner
