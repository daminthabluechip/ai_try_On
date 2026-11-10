import '@google/model-viewer'

function Model3DViewer({ modelUrl }) {
  return (
    <div className="mx-auto max-w-md">
      <model-viewer
        src={modelUrl}
        alt="Rotatable 3D model of the try-on result"
        camera-controls=""
        auto-rotate=""
        shadow-intensity="1"
        touch-action="pan-y"
        style={{ width: '100%', height: '420px', backgroundColor: '#f5f5f4', borderRadius: '0.75rem' }}
      />
      <p className="mt-2 text-center text-xs text-muted">Drag to rotate · scroll or pinch to zoom</p>
    </div>
  )
}

export default Model3DViewer
