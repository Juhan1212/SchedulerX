import { CanvasRenderingTarget2D } from "fancy-canvas";
import { type DrawingOptions, setLineStyle } from "../drawing";
import { DrawingPaneRenderer } from "../pane-renderer";
import type { ViewPoint } from "../pane-view";

export class HorizontalLinePaneRenderer extends DrawingPaneRenderer {
  _point: ViewPoint = { x: null, y: null };
  _isHovered: boolean;

  constructor(point: ViewPoint, options: DrawingOptions, isHovered: boolean) {
    super(options);
    this._point = point;
    this._isHovered = isHovered;
  }

  draw(target: CanvasRenderingTarget2D) {
    target.useBitmapCoordinateSpace((scope) => {
      if (this._point.y == null) return;
      const ctx = scope.context;

      const scaledY = Math.round(this._point.y * scope.verticalPixelRatio);
      const scaledX = this._point.x
        ? this._point.x * scope.horizontalPixelRatio
        : 0;

      ctx.lineWidth = this._options.width;
      ctx.strokeStyle = this._options.lineColor;
      setLineStyle(ctx, this._options.lineStyle);
      ctx.beginPath();

      ctx.moveTo(scaledX, scaledY);
      ctx.lineTo(scope.bitmapSize.width, scaledY);

      ctx.stroke();

      if (!this._isHovered) return;
      const centerX = Math.round(scope.bitmapSize.width / 2);
      this._drawMiddleCircle(scope, centerX, scaledY);
    });
  }
}
