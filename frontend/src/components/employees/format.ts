import type { components } from "@/lib/api/schema";

type ReferenceData = components["schemas"]["ReferenceData"];

type Named = { first_name: string; last_name: string };

/** "Lena Müller". */
export function fullName(employee: Named): string {
  return `${employee.first_name} ${employee.last_name}`;
}

/** "Germany" for "DE"; the code itself if the reference data doesn't know it. */
export function countryName(code: string, reference: ReferenceData): string {
  return reference.countries.find((c) => c.code === code)?.name ?? code;
}

/** "Customer Success Manager, L2", as the printout writes a role and level. */
export function roleAndLevel(employee: {
  job_role: { title: string };
  level: string;
}): string {
  return `${employee.job_role.title}, ${employee.level}`;
}

/** The minor-unit exponent of a currency, from GET /reference; null if it isn't listed. */
export function exponentOf(
  currency: string,
  reference: ReferenceData,
): number | null {
  return (
    reference.currencies.find((c) => c.code === currency)?.exponent ?? null
  );
}
