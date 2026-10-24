"use client";

import { ChevronDownIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useMe } from "@/components/shell/me-context";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api/client";
import { toProblem } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";
import { toExportQuery, type ExportFormat } from "@/lib/directory-params";
import { attachmentName, saveFile } from "@/lib/download";

import { useDirectoryState } from "./directory-state";

type ReferenceData = components["schemas"]["ReferenceData"];

const FORMATS: { format: ExportFormat; label: string }[] = [
  { format: "csv", label: "CSV" },
  { format: "xlsx", label: "Excel (.xlsx)" },
];

/**
 * Downloads GET /employees/export with exactly the directory's filters and sort ("what you
 * see is what you export", docs/11-import-export.md §6). Without SALARY_READ the API leaves
 * the salary columns out, and the label says so (docs/13-frontend-ux.md §3.5).
 */
export function ExportMenu({ reference }: { reference: ReferenceData }) {
  const me = useMe();
  const [state] = useDirectoryState();
  const [pending, setPending] = useState(false);
  const canReadSalaries = me.can("SALARY_READ");

  async function download(format: ExportFormat) {
    setPending(true);
    try {
      const { data, error, response } = await api.GET(
        "/api/v1/employees/export",
        {
          params: {
            query: toExportQuery(state, format, { canReadSalaries, reference }),
          },
          parseAs: "blob",
        },
      );
      if (data) {
        saveFile(data, attachmentName(response, `acme-employees.${format}`));
      } else {
        const problem = await toProblem(response, error);
        toast.error(`Couldn't export: ${problem.detail ?? problem.title}`);
      }
    } catch {
      toast.error("Couldn't export: the connection failed. Try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" disabled={pending} className="font-normal">
          {canReadSalaries ? "Export" : "Export (no salary data)"}
          <ChevronDownIcon aria-hidden="true" className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {FORMATS.map(({ format, label }) => (
          <DropdownMenuItem key={format} onSelect={() => void download(format)}>
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
