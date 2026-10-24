"use client";

import { parseAsInteger, useQueryState } from "nuqs";
import { useState } from "react";

import { api } from "@/lib/api/client";
import { toProblem } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";

import { explainUploadProblem, type Explained } from "./messages";
import { ReviewStep } from "./review-step";
import { UploadStep } from "./upload-step";

type ImportJobReport = components["schemas"]["ImportJobReport"];
type UploadBody =
  components["schemas"]["Body_upload_import_api_v1_imports_post"];

const COULD_NOT_UPLOAD: Explained = {
  message: "Couldn't reach the server, so the file wasn't checked.",
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

  function uploadAgain() {
    setReport(null);
    void setJob(null);
  }

  const shown = report && report.id === job ? report : null;
  if (shown) return <ReviewStep report={shown} onUploadAgain={uploadAgain} />;
  return (
    <UploadStep
      uploading={uploading}
      error={uploadError}
      onFile={(file) => void upload(file)}
    />
  );
}
