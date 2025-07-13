import { RayLinePaneRenderer } from "./pane-renderer";
import { RayLine } from "./ray-line";
import { DrawingPaneView, type ViewPoint } from "../pane-view";
import { InteractionState } from "../drawing";

export class RayLinePaneView extends DrawingPaneView {
  _source: RayLine;
  _point: ViewPoint = { x: null, y: null };

  constructor(source: RayLine) {
    super(source);
    this._source = source;
  }

  update() {
    const point = this._source._point;
    const timeScale = this._source.chart.timeScale();
    const series = this._source.series;
    this._point.x = point.time
      ? timeScale.timeToCoordinate(point.time)
      : timeScale.logicalToCoordinate(point.logical);
    this._point.y = series.priceToCoordinate(point.price);
  }

  renderer() {
    return new RayLinePaneRenderer(
      this._point,
      this._source._options,
      this._source.state === InteractionState.HOVERING
    );
  }
}
