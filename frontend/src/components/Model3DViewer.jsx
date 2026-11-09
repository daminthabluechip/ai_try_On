// =====================================================================
// Model3DViewer.jsx  —  shows a 3D model (.glb) you can rotate 360°.
// =====================================================================
// Uses <model-viewer>, a free web component made by Google:
//   https://modelviewer.dev
// It is a custom HTML tag, so React can use it like a normal element
// once the library is imported (the import "registers" the tag).
//
// What the user can do:
//   - drag (mouse or finger) to rotate the model in any direction
//   - scroll / pinch to zoom
//   - it slowly turns by itself until the user touches it (auto-rotate)
//
// Props:
//   modelUrl -> address of the .glb file from the backend

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
        // "pan-y" lets phone users still scroll the page up/down.
        touch-action="pan-y"
        style={{ width: '100%', height: '420px', backgroundColor: '#f5f5f4', borderRadius: '0.75rem' }}
      />
      <p className="mt-2 text-center text-xs text-muted">Drag to rotate · scroll or pinch to zoom</p>
    </div>
  )
}

export default Model3DViewer
