/**
 * Hands a downloaded file to the browser to save. A module of its own so tests can mock it:
 * jsdom has no object URLs and saves nothing.
 */
export function saveFile(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  // Give the browser a moment to start the download before the URL goes.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** The file name a response's `Content-Disposition` gives, else `fallback`. */
export function attachmentName(response: Response, fallback: string): string {
  const header = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/i.exec(header);
  return match?.[1]?.trim() || fallback;
}
