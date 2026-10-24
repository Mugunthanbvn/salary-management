"use client";

import { useState } from "react";

import { useMe } from "@/components/shell/me-context";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";

import { SalaryChangeDialog } from "./salary-change-form";

type EmployeeDetail = components["schemas"]["EmployeeDetail"];
type ReferenceData = components["schemas"]["ReferenceData"];

type Open = "salary" | "edit" | "terminate" | "reactivate" | null;

/**
 * The employee's actions, each shown only to someone whose permissions allow it (the API
 * still checks): Record salary change (SALARY_WRITE), Edit details and Terminate or
 * Reactivate (EMPLOYEE_WRITE). On a phone the main action sits in a bar fixed above the
 * bottom navigation (DESIGN.md "Mobile").
 */
export function EmployeeActions({
  employee,
  reference,
}: {
  employee: EmployeeDetail;
  reference: ReferenceData;
}) {
  const me = useMe();
  const [open, setOpen] = useState<Open>(null);
  // The version is what every change sends back; callers without SALARY_READ don't get it.
  const version = employee.version;
  if (version === null) return null;
  const active = employee.status === "ACTIVE";
  const canChangeSalary = me.can("SALARY_WRITE") && active;
  const canEdit = me.can("EMPLOYEE_WRITE");
  if (!canChangeSalary && !canEdit) return null;

  return (
    <>
      {canEdit ? (
        active ? (
          <Button variant="destructive" onClick={() => setOpen("terminate")}>
            Terminate
          </Button>
        ) : (
          <Button variant="secondary" onClick={() => setOpen("reactivate")}>
            Reactivate
          </Button>
        )
      ) : null}
      {canEdit ? (
        <Button variant="secondary" onClick={() => setOpen("edit")}>
          Edit details
        </Button>
      ) : null}
      {canChangeSalary ? (
        <>
          <Button
            className="hidden sm:inline-flex"
            onClick={() => setOpen("salary")}
          >
            Record salary change
          </Button>
          <div
            data-slot="phone-action-bar"
            className="fixed inset-x-0 bottom-[calc(3.5rem+env(safe-area-inset-bottom))] z-30 border-t border-rule bg-paper py-3 page-gutter sm:hidden"
          >
            <Button
              className="min-h-13 w-full text-base"
              onClick={() => setOpen("salary")}
            >
              Record salary change
            </Button>
          </div>
          <SalaryChangeDialog
            open={open === "salary"}
            onOpenChange={(next) => setOpen(next ? "salary" : null)}
            employee={employee}
            reference={reference}
            version={version}
          />
        </>
      ) : null}
    </>
  );
}
