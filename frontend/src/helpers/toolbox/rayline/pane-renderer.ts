import { CanvasRenderingTarget2D } from "fancy-canvas";
import { type DrawingOptions, setLineStyle } from "../drawing";
import { DrawingPaneRenderer } from "../pane-renderer";
import type { ViewPoint } from "../pane-view";

export class RayLinePaneRenderer extends DrawingPaneRenderer {
  _point: ViewPoint = { x: null, y: null };
  _isHovered: boolean;

  constructor(point: ViewPoint, options: DrawingOptions, isHovered: boolean) {
    super(options);
    this._point = point;
    this._isHovered = isHovered;
  }

  draw(target: CanvasRenderingTarget2D) {
    target.useBitmapCoordinateSpace((scope) => {
      if (this._point.y == null || this._point.x == null) return;
      const ctx = scope.context;

      const scaledY = Math.round(this._point.y * scope.verticalPixelRatio);
      const scaledX = this._point.x * scope.horizontalPixelRatio;

      ctx.lineWidth = this._options.width;
      ctx.strokeStyle = this._options.lineColor;
      setLineStyle(ctx, this._options.lineStyle);
      ctx.beginPath();

      ctx.moveTo(scaledX, scaledY);
      ctx.lineTo(scope.bitmapSize.width, scaledY);

      ctx.stroke();

      if (!this._isHovered) return;
      this._drawMiddleCircle(scope, scaledX, scaledY); // scaledX에 원을 그림
    });
  }
}
