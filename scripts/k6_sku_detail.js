import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 30,
  duration: "60s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<50"],
  },
};

export default function () {
  const apiBase = __ENV.API_BASE_URL || "http://replace_me_api_host:8000";
  const url = `${apiBase}/api/sku/detail/SKU001/`;
  const res = http.get(url, { headers: { "X-Request-ID": `k6-${__VU}-${__ITER}` } });
  check(res, { "status is 200": (r) => r.status === 200 });
  sleep(0.1);
}
