import type { BarData, Time } from "lightweight-charts";
import type { CandleBarData } from "../types/marketInfo";
import type { ErrorResponseValue } from "../types/response";

export function isBarData(obj: unknown): obj is BarData<Time> {
  return (
    obj !== null &&
    typeof obj === "object" &&
    "time" in obj &&
    "open" in obj &&
    "high" in obj &&
    "low" in obj &&
    "close" in obj
  );
}

export function isCandleBarData(x: unknown): x is CandleBarData {
  return (
    x !== null &&
    typeof x === "object" &&
    "channel" in x &&
    x.channel === "kline" &&
    "time" in x &&
    "open" in x &&
    "high" in x &&
    "low" in x &&
    "close" in x &&
    "volume" in x
  );
}

export function isErrorResponse(data: unknown): data is ErrorResponseValue {
  return data !== null && typeof data === "object" && "error" in data;
}
