type ApiStatusProps = {
  status: "ok" | "unreachable";
};

export function ApiStatus({ status }: ApiStatusProps) {
  return <p role="status">{status === "ok" ? "API: ok" : "API unreachable"}</p>;
}
