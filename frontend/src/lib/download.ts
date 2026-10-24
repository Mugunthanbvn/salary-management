/**
 * Hands a downloaded file to the browser to save. A module of its own so tests can mock it:
 * jsdom has no object URLs and saves nothing.
 */
export function saveFile(blob: Blob, filename: string): void {
  void blob;
  void filename;
  throw new Error("saveFile is not implemented yet");
}
