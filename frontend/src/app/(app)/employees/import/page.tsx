import type { Metadata } from "next";
import { Suspense } from "react";

import { ImportFlow } from "@/components/import/import-flow";
import { Forbidden } from "@/components/print";
import { PageSkeleton } from "@/components/shell/skeletons";
import { getMe } from "@/lib/api/me";
import { can } from "@/lib/permissions";

export const metadata: Metadata = { title: "Import employees" };

/**
 * Bulk import (docs/13-frontend-ux.md §4.7): upload a file, check it, import it. Everything
 * after the permission check happens in the browser: the upload is a client fetch through
 * the /api rewrite. ImportFlow reads `?job=` from the URL, hence its own Suspense boundary.
 */
export default async function ImportPage() {
  const me = await getMe();
  if (!can(me, "IMPORT")) return <Forbidden />;
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ImportFlow />
    </Suspense>
  );
}
