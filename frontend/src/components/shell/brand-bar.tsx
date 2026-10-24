/** The top bar with only the name, for pages outside the signed-in shell. */
export function BrandBar() {
  return (
    <header className="border-b border-rule pt-[env(safe-area-inset-top)]">
      <div className="mx-auto max-w-[1280px] px-4 py-1 sm:px-8 sm:py-2">
        <span className="inline-flex min-h-11 items-center font-serif text-[20px] font-bold sm:text-[22px]">
          ACME Pay
        </span>
      </div>
    </header>
  );
}
