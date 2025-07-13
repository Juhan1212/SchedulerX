import type {
  DataChangedScope,
  IChartApi,
  ISeriesApi,
  ISeriesPrimitive,
  SeriesAttachedParameter,
  SeriesOptionsMap,
  Time,
} from "lightweight-charts";

/**
 * Ensures that value is defined.
 * Throws if the value is undefined, returns the original value otherwise.
 *
 * @param value - The value, or undefined.
 * @returns The passed value, if it is not undefined
 */
export function ensureDefined(value: undefined): never;
export function ensureDefined<T>(value: T | undefined): T;
export function ensureDefined<T>(value: T | undefined): T {
  if (value === undefined) {
    throw new Error("Value is undefined");
  }

  return value;
}

/**
 * Ensures that value is not null.
 * Throws if the value is null, returns the original value otherwise.
 *
 * @param value - The value, or null.
 * @returns The passed value, if it is not null
 */
export function ensureNotNull(value: null): never;
export function ensureNotNull<T>(value: T | null): T;
export function ensureNotNull<T>(value: T | null): T {
  if (value === null) {
    throw new Error("Value is null");
  }

  return value;
}

//* PluginBase is a useful base to build a plugin upon which
//* already handles creating getters for the chart and series,
//* and provides a requestUpdate method.
export abstract class PluginBase implements ISeriesPrimitive<Time> {
  private _chart: IChartApi | undefined = undefined;
  private _series: ISeriesApi<keyof SeriesOptionsMap> | undefined = undefined;

  protected dataUpdated?(scope: DataChangedScope): void;
  protected requestUpdate(): void {
    if (this._requestUpdate) this._requestUpdate();
  }
  private _requestUpdate?: () => void;

  public attached({
    chart,
    series,
    requestUpdate,
  }: SeriesAttachedParameter<Time>) {
    this._chart = chart;
    this._series = series;
    this._series.subscribeDataChanged(this._fireDataUpdated.bind(this)); // bind(this)를 사용하여 인스턴스를 가리키게 됨
    this._requestUpdate = requestUpdate;
    this.requestUpdate();
  }

  public detached() {
    this._chart = undefined;
    this._series = undefined;
    this._requestUpdate = undefined;
  }

  public get chart(): IChartApi {
    return ensureDefined(this._chart);
  }

  public get series(): ISeriesApi<keyof SeriesOptionsMap> {
    return ensureDefined(this._series);
  }

  private _fireDataUpdated(scope: DataChangedScope) {
    if (this.dataUpdated) {
      this.dataUpdated(scope);
    }
  }
}
