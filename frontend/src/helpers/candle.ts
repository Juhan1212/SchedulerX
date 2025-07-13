import { FuturesCandlestick } from "gate-api";

export interface CandleData {
  candleData: {
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
  }[];
  volumeData: {
    time: number;
    value: number;
    color?: string;
  }[];
  ex1VolumeData?: {
    time: number;
    value: number;
    color?: string;
  }[];
  ex2VolumeData?: {
    time: number;
    value: number;
    color?: string;
  }[];
  usdtCandleData?: {
    time: number;
    value: number;
  }[];
}

export interface CandlestickParams {
  exchange: string;
  symbol: string;
  interval: string;
  from?: number;
  to?: number;
  limit?: number;
}

export const transformDataIntoCandleData = (
  data: FuturesCandlestick[]
): CandleData => {
  const candleData = data.map((item: FuturesCandlestick) => {
    return {
      time: item.t !== undefined ? parseInt(item.t.toString()) : 0,
      open: parseFloat(item.o ?? "0"),
      high: parseFloat(item.h ?? "0"),
      low: parseFloat(item.l ?? "0"),
      close: parseFloat(item.c ?? "0"),
    };
  });

  const volumeData = data.map((item: FuturesCandlestick) => {
    return {
      time: item.t !== undefined ? parseInt(item.t.toString()) : 0,
      value: parseFloat(item.v?.toString() ?? "0"),
    };
  });

  return { candleData, volumeData };
};
