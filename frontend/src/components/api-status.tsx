type ApiStatusProps = {
  status: "ok";
};

export function ApiStatus({ status }: ApiStatusProps) {
  return <p role="status">API: {status}</p>;
}
