import type {
  Coordinate,
  IChartApi,
  ISeriesApi,
  Logical,
  MouseEventParams,
  SeriesType,
} from "lightweight-charts";
import { Drawing } from "./drawing";
import { HorizontalLine } from "./horizontalLine/horizontal-line";
import { TrendLine } from "./trendline/trend-line";
import { RayLine } from "./rayline/ray-line";
import { VerticalLine } from "./verticalLine/vertical-line";

// Define a type union for all drawing constructors
// Updated type for drawing constructors
type DrawingConstructor =
  | typeof TrendLine
  | typeof HorizontalLine
  | typeof RayLine
  | typeof VerticalLine;

export class DrawingTool {
  private _chart: IChartApi;
  private _series: ISeriesApi<SeriesType>;
  private _finishDrawingCallback: (() => void) | null = null;

  private _drawings: Drawing[] = [];
  private _activeDrawing: Drawing | null = null;
  private _isDrawing: boolean = false;
  private _drawingType: DrawingConstructor | null = null;

  constructor(
    chart: IChartApi,
    series: ISeriesApi<SeriesType>,
    finishDrawingCallback: (() => void) | null = null
  ) {
    this._chart = chart;
    this._series = series;
    this._finishDrawingCallback = finishDrawingCallback;
    this._chart.subscribeClick(this._clickHandler);
    this._chart.subscribeCrosshairMove(this._moveHandler);
  }

  private _clickHandler = (param: MouseEventParams) => this._onClick(param);
  private _moveHandler = (param: MouseEventParams) => this._onMouseMove(param);

  beginDrawing(DrawingType: DrawingConstructor) {
    this._chart.applyOptions({ handleScroll: false });
    this._drawingType = DrawingType;
    this._isDrawing = true;
    this._addTouchEventListeners();
  }

  stopDrawing() {
    this._chart.applyOptions({ handleScroll: true });
    this._isDrawing = false;
    this._activeDrawing = null;
    this._removeTouchEventListeners();
  }

  get drawings() {
    return this._drawings;
  }

  addNewDrawing(drawing: Drawing) {
    this._series.attachPrimitive(drawing);
    this._drawings.push(drawing);
  }

  delete(d: Drawing | null) {
    if (d == null) return;
    const idx = this._drawings.indexOf(d);
    if (idx == -1) return;
    this._drawings.splice(idx, 1);
    d.detach();
  }

  clearDrawings() {
    for (const d of this._drawings) d.detach();
    this._drawings = [];
  }

  repositionOnTime() {
    for (const drawing of this.drawings) {
      const newPoints = [];
      for (const point of drawing.points) {
        if (!point) {
          newPoints.push(point);
          continue;
        }
        const logical = point.time
          ? this._chart
              .timeScale()
              .coordinateToLogical(
                this._chart.timeScale().timeToCoordinate(point.time) || 0
              )
          : point.logical;
        newPoints.push({
          time: point.time,
          logical: logical as Logical,
          price: point.price,
        });
      }
      drawing.updatePoints(...newPoints);
    }
  }

  private _onClick(param: MouseEventParams) {
    if (!this._isDrawing) {
      this._onMouseMove(param);
      return;
    }

    const point = Drawing._eventToPoint(param, this._series);
    if (!point) return;

    if (this._activeDrawing == null) {
      if (this._drawingType == null) return;
      this._activeDrawing = new this._drawingType(point, point);
      this._series.attachPrimitive(this._activeDrawing);
      if (this._activeDrawing instanceof HorizontalLine) this._onClick(param);
    } else {
      this._drawings.push(this._activeDrawing);

      this.stopDrawing();

      if (!this._finishDrawingCallback) return;
      this._finishDrawingCallback();
    }
  }

  private _onMouseMove(param: MouseEventParams) {
    if (!param) return;

    for (const t of this._drawings) t._handleHoverInteraction(param);

    if (!this._isDrawing || !this._activeDrawing) return;

    const point = Drawing._eventToPoint(param, this._series);
    if (!point) return;

    this._activeDrawing.updatePoints(null, point);
    // this._activeDrawing.setSecondPoint(point);
  }

  private _addTouchEventListeners() {
    const container = this._chart.chartElement();
    if (!container) return;

    // 모바일 터치 시작을 클릭으로 처리
    container.addEventListener("touchstart", this._touchStartHandler, {
      passive: false,
    });

    container.addEventListener("touchmove", this._touchMoveHandler, {
      passive: false,
    });

    // 모바일 터치 종료를 클릭으로 처리 (두 번째 점)
    container.addEventListener("touchend", this._touchEndHandler, {
      passive: false,
    });
  }

  private _touchStartHandler = (e: TouchEvent) => {
    if (e.touches.length !== 1) return;
    e.preventDefault(); // Prevent scrolling
    const touch = e.touches[0];
    const rect = this._chart.chartElement()?.getBoundingClientRect();
    if (!rect) return;

    const clientX = touch.clientX - rect.left;
    const clientY = touch.clientY - rect.top;
    const time = this._chart.timeScale().coordinateToTime(clientX) || undefined;
    const logical =
      this._chart.timeScale().coordinateToLogical(clientX) || undefined;
    const point = { x: clientX as Coordinate, y: clientY as Coordinate };

    const param: MouseEventParams = {
      time,
      logical,
      point,
      seriesData: new Map(),
    };
    this._onClick(param);
  };

  private _removeTouchEventListeners() {
    const container = this._chart.chartElement();
    if (!container) return;

    container.removeEventListener("touchstart", this._touchStartHandler);
    container.removeEventListener("touchmove", this._touchMoveHandler);
    container.removeEventListener("touchend", this._touchEndHandler);
  }

  private _touchMoveHandler = (e: TouchEvent) => {
    if (e.touches.length !== 1) return;
    e.preventDefault(); // Prevent scrolling

    const touch = e.touches[0];
    const rect = this._chart.chartElement()?.getBoundingClientRect();
    if (!rect) return;

    const clientX = touch.clientX - rect.left;
    const clientY = touch.clientY - rect.top;
    const time = this._chart.timeScale().coordinateToTime(clientX) || undefined;
    const logical =
      this._chart.timeScale().coordinateToLogical(clientX) || undefined;
    const point = { x: clientX as Coordinate, y: clientY as Coordinate };

    const param: MouseEventParams = {
      time,
      logical,
      point,
      seriesData: new Map(),
    };
    this._onMouseMove(param);
  };

  private _touchEndHandler = (e: TouchEvent) => {
    if (!this._isDrawing || e.changedTouches.length !== 1) return;
    e.preventDefault();
    const touch = e.changedTouches[0];
    const rect = this._chart.chartElement()?.getBoundingClientRect();
    if (!rect) return;

    const clientX = touch.clientX - rect.left;
    const clientY = touch.clientY - rect.top;
    const time = this._chart.timeScale().coordinateToTime(clientX) || undefined;
    const logical =
      this._chart.timeScale().coordinateToLogical(clientX) || undefined;
    const point = { x: clientX as Coordinate, y: clientY as Coordinate };

    const param: MouseEventParams = {
      time,
      logical,
      point,
      seriesData: new Map(),
    };
    this._onClick(param);
  };
}
