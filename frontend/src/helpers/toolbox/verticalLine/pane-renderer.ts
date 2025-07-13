import { CanvasRenderingTarget2D } from "fancy-canvas";
import { type DrawingOptions, setLineStyle } from "../drawing";
import { DrawingPaneRenderer } from "../pane-renderer";
import type { ViewPoint } from "../pane-view";

export class VerticalLinePaneRenderer extends DrawingPaneRenderer {
  _point: ViewPoint = { x: null, y: null };
  _isHovered: boolean;

  constructor(point: ViewPoint, options: DrawingOptions, isHovered: boolean) {
    super(options);
    this._point = point;
    this._isHovered = isHovered;
  }

  draw(target: CanvasRenderingTarget2D) {
    target.useBitmapCoordinateSpace((scope) => {
      if (this._point.x == null) return;
      const ctx = scope.context;
      const scaledX = this._point.x * scope.horizontalPixelRatio;

      ctx.lineWidth = this._options.width;
      ctx.strokeStyle = this._options.lineColor;
      setLineStyle(ctx, this._options.lineStyle);

      ctx.beginPath();
      ctx.moveTo(scaledX, 0);
      ctx.lineTo(scaledX, scope.bitmapSize.height);
      ctx.stroke();

      if (!this._isHovered) return;
      const centerY = Math.round(scope.bitmapSize.height / 2);
      this._drawMiddleCircle(scope, scaledX, centerY);
    });
  }
}
