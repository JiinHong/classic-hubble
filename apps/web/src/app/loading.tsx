export default function Loading() {
  return (
    <main
      aria-busy="true"
      role="status"
      className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
    >
      <span className="sr-only">불러오는 중입니다.</span>
      <div aria-hidden="true" className="motion-safe:animate-pulse">
        <div className="h-8 w-48 rounded bg-stone-200" />
        <div className="mt-6 h-12 w-full rounded bg-stone-200" />
        <div className="mt-8 grid gap-6 sm:grid-cols-2">
          <div className="h-56 rounded bg-stone-100" />
          <div className="h-56 rounded bg-stone-100" />
        </div>
      </div>
    </main>
  );
}
