import type { IChartApi, ISeriesApi, SeriesType } from "lightweight-charts";
import { useCallback, useEffect, useRef, useState } from "react";
import { Drawing } from "../../helpers/toolbox/drawing";
import { DrawingTool } from "../../helpers/toolbox/drawing-tool";
import { HorizontalLine } from "../../helpers/toolbox/horizontalLine/horizontal-line";
import { RayLine } from "../../helpers/toolbox/rayline/ray-line";
import { TrendLine } from "../../helpers/toolbox/trendline/trend-line";
import { VerticalLine } from "../../helpers/toolbox/verticalLine/vertical-line";
import Icon from "../shared/SVGIcon";

interface ToolBoxProps {
  chart: IChartApi;
  series: ISeriesApi<SeriesType>;
  showMACD: boolean;
  setShowMACD: (show: boolean) => void;
  showRSI: boolean;
  setShowRSI: (show: boolean) => void;
}

export const ToolBox = ({
  chart,
  series,
  showMACD,
  setShowMACD,
  showRSI,
  setShowRSI,
}: ToolBoxProps) => {
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const drawingToolRef = useRef<DrawingTool | null>(null);

  const finishDrawingCallback = useCallback(() => {
    setActiveTool(null);
  }, []);

  useEffect(() => {
    drawingToolRef.current = new DrawingTool(
      chart,
      series,
      finishDrawingCallback
    );

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!drawingToolRef.current) return;
      if (e.key === "Backspace" || e.key === "Delete") {
        drawingToolRef.current.delete(Drawing.lastHoveredObject);
        setActiveTool(null);
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      drawingToolRef.current?.clearDrawings();
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [chart, series, finishDrawingCallback]);

  const handleToolClick = useCallback(
    (tool: string) => {
      if (!drawingToolRef.current) return;

      // 동일한 도구 버튼을 두 번 클릭하면 도구를 비활성화
      if (activeTool === tool) {
        drawingToolRef.current.stopDrawing();
        setActiveTool(null);
        return;
      }

      setActiveTool((activeTool) => (activeTool === tool ? null : tool));

      if (tool === "cursor") {
        drawingToolRef.current.stopDrawing();
      } else if (tool === "trendLine") {
        drawingToolRef.current.beginDrawing(TrendLine);
      } else if (tool === "horizontalLine") {
        drawingToolRef.current.beginDrawing(HorizontalLine);
      } else if (tool === "rayLine") {
        drawingToolRef.current.beginDrawing(RayLine);
      } else if (tool === "verticalLine") {
        drawingToolRef.current.beginDrawing(VerticalLine);
      } else if (tool === "eraser") {
        drawingToolRef.current.clearDrawings();
        setActiveTool(null);
      }
    },
    [activeTool, drawingToolRef]
  );

  return (
    <div className="tool-bar-container">
      <div className="tool-bar">
        <div className="drawing-tools">
          <button
            className="tool-btn"
            title="Select"
            onClick={() => handleToolClick("cursor")}
          >
            <Icon
              type="cursor"
              className={`drawing-tool-icon ${
                activeTool === "cursor" ? "active" : ""
              }`}
            />
          </button>
          <button
            onClick={() => handleToolClick("trendLine")}
            className="tool-btn"
          >
            <Icon
              type="trendLine"
              className={`drawing-tool-icon ${
                activeTool === "trendLine" ? "active" : ""
              }`}
            />
          </button>
          <button
            onClick={() => handleToolClick("horizontalLine")}
            className="tool-btn"
          >
            <Icon
              type="horizontalLine"
              className={`drawing-tool-icon ${
                activeTool === "horizontalLine" ? "active" : ""
              }`}
            />
          </button>
          <button
            onClick={() => handleToolClick("rayLine")}
            className="tool-btn"
          >
            <Icon
              type="rayLine"
              className={`drawing-tool-icon ${
                activeTool === "rayLine" ? "active" : ""
              }`}
            />
          </button>
          <button
            onClick={() => handleToolClick("verticalLine")}
            className="tool-btn"
          >
            <Icon
              type="verticalLine"
              className={`drawing-tool-icon ${
                activeTool === "verticalLine" ? "active" : ""
              }`}
            />
          </button>
          <button
            onClick={() => handleToolClick("eraser")}
            className="tool-btn"
          >
            <Icon
              type="eraser"
              className={`drawing-tool-icon ${
                activeTool === "eraser" ? "active" : ""
              }`}
            />
          </button>
        </div>
        <div className="control-visible">
          <button
            className={`control-btn ${showMACD ? "active" : ""}`}
            title="Toggle MACD"
            onClick={() => setShowMACD(!showMACD)}
          >
            MACD
          </button>
          <button
            className={`control-btn ${showRSI ? "active" : ""}`}
            title="Toggle RSI"
            onClick={() => setShowRSI(!showRSI)}
          >
            RSI
          </button>
        </div>
      </div>
    </div>
  );
};
