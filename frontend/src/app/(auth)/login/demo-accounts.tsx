import { ROLE_LABELS } from "@/lib/roles";

// The seeded demo users (docs/12-seed-data.md §11). Their passwords come from env at seed
// time and are shared in the submission email, never shown or committed here.
const DEMO_ACCOUNTS = [
  { name: "Arun", role: ROLE_LABELS.ADMIN, email: "admin@acme.example" },
  { name: "Hema", role: ROLE_LABELS.HR_MANAGER, email: "hr@acme.example" },
  { name: "Farah", role: ROLE_LABELS.VIEWER, email: "viewer@acme.example" },
];

/** Shown on the demo deployment only (NEXT_PUBLIC_SHOW_DEMO_ACCOUNTS=true). */
export function DemoAccounts() {
  return (
    <section
      aria-labelledby="demo-accounts"
      className="min-w-0 flex-[1_1_280px] border-t border-rule pt-6 sm:max-w-[420px] lg:border-t-0 lg:border-l lg:pt-0 lg:pl-12"
    >
      <h2
        id="demo-accounts"
        className="font-serif text-[22px] leading-tight font-semibold"
      >
        Demo accounts
      </h2>
      <p className="mt-2 text-[15px] text-ink-2">
        Sign in as each role to see what it can do. A viewer never sees
        anyone&apos;s salary.
      </p>
      <ul className="mt-4">
        {DEMO_ACCOUNTS.map((account) => (
          <li
            key={account.email}
            className="border-t border-rule py-3 text-[15px] first:border-t-0"
          >
            <span className="font-bold">{account.name}</span>, {account.role}:{" "}
            <span className="break-all text-ink-2">{account.email}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 font-serif text-[15px] text-ink-2 italic">
        The passwords are in the submission email.
      </p>
    </section>
  );
}
