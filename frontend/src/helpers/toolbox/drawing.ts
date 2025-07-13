import {
  type ISeriesApi,
  type Logical,
  type MouseEventParams,
  type SeriesType,
  LineStyle,
  type Point as LPoint,
  type Time,
} from "lightweight-charts";

import { PluginBase } from "./plugin-base";
import { DrawingPaneView } from "./pane-view";

export interface Point {
  time: Time | null;
  logical: Logical;
  price: number;
}

export interface DiffPoint {
  time: Time;
  logical?: number;
  price: number;
}

export interface DrawingOptions {
  lineColor: string;
  lineStyle: LineStyle;
  width: number;
  text?: string;
}

export const defaultOptions: DrawingOptions = {
  lineColor: "#1E80F0",
  lineStyle: LineStyle.Solid,
  width: 4,
};

export function setLineStyle(
  ctx: CanvasRenderingContext2D,
  style: LineStyle
): void {
  const dashPatterns = {
    [LineStyle.Solid]: [],
    [LineStyle.Dotted]: [ctx.lineWidth, ctx.lineWidth],
    [LineStyle.Dashed]: [2 * ctx.lineWidth, 2 * ctx.lineWidth],
    [LineStyle.LargeDashed]: [6 * ctx.lineWidth, 6 * ctx.lineWidth],
    [LineStyle.SparseDotted]: [ctx.lineWidth, 4 * ctx.lineWidth],
  };

  const dashPattern = dashPatterns[style];
  ctx.setLineDash(dashPattern);
}

export const InteractionState = {
  NONE: 0,
  HOVERING: 1,
  DRAGGING: 2,
  DRAGGINGP1: 3,
  DRAGGINGP2: 4,
  DRAGGINGP3: 5,
  DRAGGINGP4: 6,
} as const;
export type InteractionState =
  (typeof InteractionState)[keyof typeof InteractionState];

export abstract class Drawing extends PluginBase {
  _paneViews: DrawingPaneView[] = [];
  _options: DrawingOptions;

  abstract _type: string;
  protected _points: (Point | null)[] = [];

  protected _state: InteractionState = InteractionState.NONE;

  protected _startDragPoint: Point | null = null;
  protected _latestHoverPoint: LPoint | undefined = undefined;

  protected static _mouseIsDown: boolean = false;

  public static hoveredObject: Drawing | null = null;
  public static lastHoveredObject: Drawing | null = null;

  protected _listeners: {
    name: keyof DocumentEventMap;
    listener: EventListenerOrEventListenerObject;
  }[] = [];

  constructor(options?: Partial<DrawingOptions>) {
    super();
    this._options = {
      ...defaultOptions,
      ...options,
    };
  }

  // protected dataUpdated(scope: DataChangedScope): void {
  //   this.requestUpdate()
  // }

  updateAllViews() {
    this._paneViews.forEach((pw) => pw.update());
  }

  paneViews() {
    return this._paneViews;
  }

  applyOptions(options: Partial<DrawingOptions>) {
    this._options = {
      ...this._options,
      ...options,
    };
    this.requestUpdate();
  }

  public updatePoints(...points: (Point | null)[]) {
    for (let i = 0; i < this.points.length; i++) {
      if (points[i] == null) continue;
      this.points[i] = points[i] as Point;
    }
    this.requestUpdate();
  }

  detach() {
    this._options.lineColor = "transparent";
    this.requestUpdate();
    this.series.detachPrimitive(this);
    for (const s of this._listeners) {
      document.body.removeEventListener(s.name, s.listener);
    }
  }

  get points() {
    return this._points;
  }

  get state(): InteractionState {
    return this._state;
  }

  protected _subscribe(
    name: keyof DocumentEventMap,
    listener: EventListenerOrEventListenerObject
  ) {
    // document.body.addEventListener(name, listener)
    const target = this.chart.chartElement() || document;
    target.addEventListener(name, listener, { passive: false });
    this._listeners.push({ name: name, listener: listener });
  }

  protected _unsubscribe(
    name: keyof DocumentEventMap,
    callback: EventListenerOrEventListenerObject
  ) {
    // document.body.removeEventListener(name, callback)
    const target = this.chart.chartElement() || document;
    target.removeEventListener(name, callback);

    const toRemove = this._listeners.find(
      (x) => x.name === name && x.listener === callback
    );
    if (toRemove) {
      this._listeners.splice(this._listeners.indexOf(toRemove), 1);
    }
  }

  _handleHoverInteraction(param: MouseEventParams) {
    this._latestHoverPoint = param.point;
    if (Drawing._mouseIsDown) {
      this._handleDragInteraction(param);
    } else {
      if (this._mouseIsOverDrawing(param)) {
        if (this._state != InteractionState.NONE) return;
        this._moveToState(InteractionState.HOVERING);
        Drawing.hoveredObject = Drawing.lastHoveredObject = this;
      } else {
        if (this._state == InteractionState.NONE) return;
        this._moveToState(InteractionState.NONE);
        if (Drawing.hoveredObject === this) Drawing.hoveredObject = null;
      }
    }
  }

  // 마우스 클릭시, 해당 Point를 반환
  public static _eventToPoint(
    param: MouseEventParams,
    series: ISeriesApi<SeriesType>
  ) {
    if (!series || !param.point || !param.logical) return null;
    const barPrice = series.coordinateToPrice(param.point.y);
    if (barPrice == null) return null;
    return {
      time: param.time || null,
      logical: param.logical,
      price: barPrice.valueOf(),
    };
  }

  protected static _getDiff(p1: Point, p2: Point): DiffPoint {
    const diff: DiffPoint = {
      time: (Number(p1.time) - Number(p2.time)) as Time,
      // ASIS : logical: p1.logical - p2.logical,
      price: p1.price - p2.price,
    };
    return diff;
  }

  protected _addDiffToPoint(
    point: Point | null,
    timeDiff: Time,
    priceDiff: number
  ) {
    if (!point) return;

    // ASIS : point.logical = (point.logical + logicalDiff) as Logical
    point.price = point.price + priceDiff;
    point.time = (Number(point.time) + Number(timeDiff)) as Time;
    const coordinate = this.chart.timeScale().timeToCoordinate(point.time);
    if (!coordinate) {
      // console.log('coordinate is null')
      // HorizontalLine은 time이 없으므로, coordinate가 null이 될 수 있음
      return;
    }
    // ASIS : point.time = this.series.dataByIndex(point.logical)?.time || null
    const logical = this.chart.timeScale().coordinateToLogical(coordinate);
    if (!logical) {
      return;
    }
    point.logical = logical;
  }

  protected _handleMouseDownInteraction = () => {
    // if (Drawing._mouseIsDown) return;
    Drawing._mouseIsDown = true;
    this._onMouseDown();
  };

  protected _handleMouseUpInteraction = () => {
    // if (!Drawing._mouseIsDown) return;
    Drawing._mouseIsDown = false;
    this._moveToState(InteractionState.HOVERING);
  };

  private _handleDragInteraction(param: MouseEventParams): void {
    if (
      this._state != InteractionState.DRAGGING &&
      this._state != InteractionState.DRAGGINGP1 &&
      this._state != InteractionState.DRAGGINGP2 &&
      this._state != InteractionState.DRAGGINGP3 &&
      this._state != InteractionState.DRAGGINGP4
    ) {
      return;
    }
    const mousePoint = Drawing._eventToPoint(param, this.series);
    if (!mousePoint) return;
    this._startDragPoint = this._startDragPoint || mousePoint; // 처음에는 null이므로, mousePoint로 초기화

    const diff = Drawing._getDiff(mousePoint, this._startDragPoint);
    this._onDrag(diff);
    this.requestUpdate();

    this._startDragPoint = mousePoint; // 다음 drag를 위해 startDragPoint를 업데이트
  }

  protected abstract _onMouseDown(): void;
  protected abstract _onDrag(diff: DiffPoint): void;
  protected abstract _moveToState(state: InteractionState): void;
  protected abstract _mouseIsOverDrawing(param: MouseEventParams): boolean;
}
