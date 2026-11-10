import { Link } from 'react-router-dom'

// TODO: Change these texts to describe your project in your own words.
const HOW_IT_WORKS_STEPS = [
  {
    icon: '📷',
    title: 'Upload your photo',
    text: 'Take or choose a clear, front-facing photo of yourself.',
  },
  {
    icon: '👗',
    title: 'Pick a garment',
    text: 'Browse the catalog and choose the item you want to try.',
  },
  {
    icon: '✨',
    title: 'See the result',
    text: 'Our AI creates a preview of you wearing it. Compare and download.',
  },
]

function HomePage() {
  return (
    <div>
      <section className="bg-gradient-to-b from-brand-light to-canvas">
        <div className="mx-auto max-w-6xl px-4 py-20 text-center sm:py-28">
          <p className="text-sm font-medium tracking-widest text-brand uppercase">
            AI-powered fashion
          </p>
          {/* TODO: Change the main headline and description here. */}
          <h1 className="mx-auto mt-4 max-w-3xl font-display text-4xl leading-tight font-semibold sm:text-6xl">
            See it on you <span className="text-brand italic">before</span> you buy it.
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-base text-muted sm:text-lg">
            AI Virtual Try-On lets you upload a photo, choose clothing from our catalog
            and instantly preview how it looks on you.
          </p>

          <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              to="/try-on"
              className="rounded-full bg-brand px-8 py-3 font-medium text-white shadow-sm transition hover:bg-brand-dark"
            >
              Start Try-On
            </Link>
            <Link
              to="/catalog"
              className="rounded-full border border-ink px-8 py-3 font-medium transition hover:bg-ink hover:text-white"
            >
              Browse Catalog
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-center font-display text-3xl font-semibold">How it works</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {HOW_IT_WORKS_STEPS.map((step, index) => (
            <div key={step.title} className="rounded-2xl border border-stone-200 bg-white p-6 text-center">
              <div className="text-4xl">{step.icon}</div>
              <p className="mt-3 text-xs font-medium text-brand">STEP {index + 1}</p>
              <h3 className="mt-1 font-display text-xl font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm text-muted">{step.text}</p>
            </div>
          ))}
        </div>

        <p className="mx-auto mt-10 max-w-2xl text-center text-xs text-muted">
          Note: the try-on image shows how a garment may <em>look</em>. It does not
          guarantee real-world size or fit.
        </p>
      </section>
    </div>
  )
}

export default HomePage
