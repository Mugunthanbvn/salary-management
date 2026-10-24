"use client";

import { parseAsInteger, useQueryState } from "nuqs";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { PageTitle } from "@/components/print";
import { api } from "@/lib/api/client";
import { toProblem } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";
import { formatCount } from "@/lib/numbers";

import { DoneStep } from "./done-step";
import { EndedStep } from "./ended-step";
import {
  explainCommitProblem,
  explainLoadProblem,
  explainUploadProblem,
  type CommitProblem,
  type Explained,
} from "./messages";
import { ReviewStep } from "./review-step";
import { UploadStep } from "./upload-step";

type ImportJobReport = components["schemas"]["ImportJobReport"];
type UploadBody =
  components["schemas"]["Body_upload_import_api_v1_imports_post"];

const COULD_NOT_UPLOAD: Explained = {
  message: "Couldn't reach the server, so the file wasn't checked.",
  more: "Check your connection and try again.",
};

const COULD_NOT_LOAD: Explained = {
  message: "Couldn't reach the server to open this check.",
  more: "Check your connection, then reload the page.",
};

const COULD_NOT_COMMIT: Explained = {
  message: "Couldn't reach the server, so nothing was imported.",
  more: "Check your connection and try again.",
};

/**
 * The import screen (docs/13-frontend-ux.md §4.7): upload, check, import. The dry-run's id
 * stays in the URL (`?job=31`), so a refresh or a shared link reopens the same check.
 * Uploads are a client fetch through the /api rewrite, never a Server Action (1 MB limit).
 */
export function ImportFlow() {
  const [job, setJob] = useQueryState(
    "job",
    parseAsInteger.withOptions({ history: "push" }),
  );
  const [report, setReport] = useState<ImportJobReport | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<Explained | null>(null);
  const [committing, setCommitting] = useState(false);
  const [commitProblem, setCommitProblem] = useState<CommitProblem | null>(
    null,
  );
  const [inserted, setInserted] = useState<number | null>(null);

  // A `?job=` the page doesn't hold yet (a refresh, a shared link): ask the API for it.
  const missing = job !== null && report?.id !== job ? job : null;
  useEffect(() => {
    if (missing === null) return;
    let current = true;
    void (async () => {
      let problem: Explained;
      try {
        const { data, error, response } = await api.GET(
          "/api/v1/imports/{import_id}",
          { params: { path: { import_id: missing } } },
        );
        if (!current) return;
        if (data) {
          setReport(data);
          return;
        }
        problem = explainLoadProblem(await toProblem(response, error));
      } catch {
        problem = COULD_NOT_LOAD;
      }
      if (!current) return;
      setUploadError(problem);
      void setJob(null);
    })();
    return () => {
      current = false;
    };
  }, [missing, setJob]);

  async function upload(file: File) {
    setUploading(file.name);
    setUploadError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const { data, error, response } = await api.POST("/api/v1/imports", {
        // openapi-typescript types the binary field as a string; openapi-fetch sends
        // FormData as is, and the browser sets the multipart boundary.
        body: form as unknown as UploadBody,
      });
      if (data) {
        // A new check: the last file's import result or problem no longer applies.
        setInserted(null);
        setCommitProblem(null);
        setReport(data);
        void setJob(data.id);
      } else {
        setUploadError(explainUploadProblem(await toProblem(response, error)));
      }
    } catch {
      setUploadError(COULD_NOT_UPLOAD);
    }
    setUploading(null);
  }

  async function commit(id: number) {
    setCommitting(true);
    setCommitProblem(null);
    try {
      const { data, error, response } = await api.POST(
        "/api/v1/imports/{import_id}/commit",
        { params: { path: { import_id: id } } },
      );
      if (data) {
        setInserted(data.inserted);
        toast.success(
          `Imported ${formatCount(data.inserted)} ${data.inserted === 1 ? "employee" : "employees"}`,
        );
      } else {
        setCommitProblem(
          explainCommitProblem(await toProblem(response, error)),
        );
      }
    } catch {
      setCommitProblem({ ...COULD_NOT_COMMIT, conflicts: [], retry: true });
    }
    setCommitting(false);
  }

  function uploadAgain() {
    setReport(null);
    setCommitProblem(null);
    setInserted(null);
    void setJob(null);
  }

  const shown = report && report.id === job ? report : null;
  if (missing !== null) return <OpeningCheck />;
  if (shown && inserted !== null) {
    return (
      <DoneStep
        inserted={inserted}
        filename={shown.filename}
        onImportAnother={uploadAgain}
      />
    );
  }
  if (shown && shown.status !== "DRY_RUN") {
    return <EndedStep report={shown} onUploadAgain={uploadAgain} />;
  }
  if (shown) {
    return (
      <ReviewStep
        report={shown}
        committing={committing}
        commitProblem={commitProblem}
        onCommit={() => void commit(shown.id)}
        onUploadAgain={uploadAgain}
      />
    );
  }
  return (
    <UploadStep
      uploading={uploading}
      error={uploadError}
      onFile={(file) => void upload(file)}
    />
  );
}

function OpeningCheck() {
  return (
    <div aria-busy="true">
      <PageTitle title="Opening the check…" />
    </div>
  );
}
