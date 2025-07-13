import type { CandleData } from "./candle";
import { getBrowserTimezoneOffset } from "./time";

export class CandleDatafeed {
  private exchange: string;
  private symbol: string;
  private interval: string;
  private _data: CandleData;

  constructor(exchange: string, symbol: string, interval: string) {
    this.exchange = exchange;
    this.symbol = symbol;
    this.interval = interval;
    this._data = {
      candleData: [],
      volumeData: [],
      ex1VolumeData: [],
      ex2VolumeData: [],
      usdtCandleData: [],
    };
  }

  getFirstDataTime() {
    return this._data.candleData[0].time;
  }

  getLatestDataTime() {
    return this._data.candleData[this._data.candleData.length - 1].time;
  }

  setData(data: CandleData) {
    this._data = data;
  }

  getData() {
    return this._data;
  }

  getExchange() {
    return this.exchange;
  }

  getSymbol() {
    return this.symbol;
  }

  getInterval() {
    return this.interval;
  }

  adjustDataByBrowserTimezone(data: CandleData): CandleData {
    return {
      candleData: data.candleData.map((candle) => ({
        ...candle,
        time: candle.time + getBrowserTimezoneOffset() * 60 * 60,
      })),
      volumeData: data.volumeData.map((volume) => ({
        ...volume,
        time: volume.time + getBrowserTimezoneOffset() * 60 * 60,
      })),
      ex1VolumeData: data.ex1VolumeData?.map((volume) => ({
        ...volume,
        time: volume.time + getBrowserTimezoneOffset() * 60 * 60,
      })),
      ex2VolumeData: data.ex2VolumeData?.map((volume) => ({
        ...volume,
        time: volume.time + getBrowserTimezoneOffset() * 60 * 60,
      })),
      usdtCandleData: data.usdtCandleData?.map((candle) => ({
        ...candle,
        time: candle.time + getBrowserTimezoneOffset() * 60 * 60,
      })),
    };
  }
}
