import type { DeepPartial, MouseEventParams } from "lightweight-charts";
import type { DiffPoint, Point, DrawingOptions } from "../drawing";
import { HorizontalLine } from "../horizontalLine/horizontal-line";
import { RayLinePaneView } from "./pane-view";

export class RayLine extends HorizontalLine {
  _type = "RayLine";

  constructor(point: Point, options: DeepPartial<DrawingOptions>) {
    super({ ...point }, options);
    this._point.time = point.time;
    this._paneViews = [new RayLinePaneView(this)];
  }

  public updatePoints(...points: (Point | null)[]) {
    for (const p of points) if (p) this._point = p;
    this.requestUpdate();
  }

  _onDrag(diff: DiffPoint) {
    this._addDiffToPoint(this._point, diff.time, diff.price);
    this.requestUpdate();
  }

  _mouseIsOverDrawing(param: MouseEventParams, tolerance = 4) {
    if (!param.point) return false;
    const y = this.series.priceToCoordinate(this._point.price);

    const x = this._point.time
      ? this.chart.timeScale().timeToCoordinate(this._point.time)
      : null;
    if (!y || !x) return false;
    return (
      Math.abs(y - param.point.y) < tolerance && param.point.x > x - tolerance
    );
  }
}
