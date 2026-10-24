import type { ApiHealth } from "@/lib/api/health";

type ApiStatusProps = {
  status: ApiHealth;
};

export function ApiStatus({ status }: ApiStatusProps) {
  return <p role="status">{status === "ok" ? "API: ok" : "API unreachable"}</p>;
}
