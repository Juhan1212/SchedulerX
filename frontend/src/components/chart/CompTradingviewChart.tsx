import { useCallback, useEffect, useRef, useState, memo } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  CandlestickSeries,
  HistogramSeries,
  type Time,
  type HistogramData,
  LineSeries,
  type LineData,
  type IPaneApi,
  type MouseEventHandler,
  type MouseEventParams,
  type LogicalRangeChangeEventHandler,
  type LogicalRange,
  createSeriesMarkers,
  createImageWatermark,
  type ISeriesMarkersPluginApi,
  type IPriceLine,
} from "lightweight-charts";
import { MACD, RSI } from "technicalindicators";
import { getTimeValue } from "../../helpers/time";
import type { Position } from "gate-api";
import type { CandleData } from "../../helpers/candle";
import { useLocation } from "react-router-dom";
import { CandleDatafeed } from "../../helpers/chart.datafeed";
import {
  alignTimeToInterval,
  getBrowserTimezoneOffset,
  intervalInSeconds,
} from "../../helpers/time";
// import { ToolBox } from "./ToolBox";
import {
  ContractSize,
  type CandleBarData,
  type PositionData,
  type TickerData,
} from "../../types/marketInfo";
import { isBarData, isCandleBarData } from "../../helpers/guard";
import { useMarkerStore } from "../../states/markerState";
import { usePriceStore } from "../../states/priceState";
import { createWebSocketStore } from "../../states/chartState";

interface TradingviewChartProps {
  positions?: Position[];
}

const CompTradingviewChart = memo(
  ({
    positions,
    store1,
    store2,
    symbol,
    interval,
    exchange1,
    exchange2,
  }: TradingviewChartProps & {
    store1: ReturnType<typeof createWebSocketStore>;
    store2: ReturnType<typeof createWebSocketStore>;
    symbol: string;
    interval: string;
    exchange1: string;
    exchange2: string;
  }) => {
    // 어드민 페이지에서만 사용되는 상태변수를 사용하기 위하여 추가
    const location = useLocation();
    const isAdminRoute = location.pathname === "/admin";

    // PriceStore에서 클릭된 가격을 관리하는 상태를 가져옴
    const { setClickedPrice } = usePriceStore();

    // PositionHistory컴포넌트에서 전역 상태로 관리하는 마커를 가져옴
    const { markers } = useMarkerStore();

    // 각 거래소의 웹소켓 스토어에서 메시지 리스너를 가져옴
    const {
      addMessageListener: addMessageListener1,
      removeMessageListener: removeMessageListener1,
    } = store1.getState();
    const {
      addMessageListener: addMessageListener2,
      removeMessageListener: removeMessageListener2,
    } = store2.getState();

    // 리렌더링되어도 차트가 초기화되지 않도록 ref로 관리
    const chartContainerRef = useRef<HTMLElement | null>(null);
    const legendRef = useRef<HTMLDivElement | null>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const volumeSeriesEx1Ref = useRef<ISeriesApi<"Histogram"> | null>(null);
    const volumeSeriesEx2Ref = useRef<ISeriesApi<"Histogram"> | null>(null);
    const lineSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const datafeedRef = useRef<CandleDatafeed | null>(null);

    // 두 거래소의 kline 데이터를 저장할 Map (time 기준)
    const klineBuffer1 = useRef<Map<number, CandleBarData>>(new Map());
    const klineBuffer2 = useRef<Map<number, CandleBarData>>(new Map());

    // subscribeVisibleLogicalRangeChange 최근 요청 시간과 로딩 상태를 관리할 ref 추가 => debouncing을 위해
    const lastRequestTimeRef = useRef<number>(0);
    const isLoadingRef = useRef<boolean>(false);

    // 최초 데이터 fetch 완료 여부
    const [initialFetchCompleted, setInitialFetchCompleted] = useState(false);

    // CSR 기반 fetcher 대체
    const [candleFetcherState, setCandleFetcherState] = useState<
      "idle" | "loading"
    >("idle");
    const [candleFetcherData, setCandleFetcherData] =
      useState<CandleData | null>(null);
    const [candleFetcherError, setCandleFetcherError] = useState<unknown>(null);

    // MACD, RSI 추가
    const [showMACD] = useState(false);
    const [showRSI] = useState(false);
    const macdSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const macdPaneRef = useRef<IPaneApi<Time> | null>(null);
    const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const rsiPaneRef = useRef<IPaneApi<Time> | null>(null);

    // 웹소켓 useEffect 최적화를 위한 ref 추가
    const crosshairVisibleRef = useRef<boolean>(false);

    // 캔들스틱 fetcher 에러핸들링을 위한 ref 추가
    const errorCountRef = useRef<number>(0);
    const lastFetchTypeRef = useRef<"initial" | "historical">("initial");
    const lastHistoricalTimeRef = useRef<number | null>(null);

    // 인터벌 변경을 추적할 ref
    const currentIntervalRef = useRef<string>(interval);
    const intervalChangeRef = useRef<boolean>(false);

    // 심볼 변경을 추적할 ref
    const currentSymbolRef = useRef<string>(symbol);
    const symbolChangeRef = useRef<boolean>(false);

    // 범례 업데이트
    const updateLegend = useCallback(
      (param: MouseEventParams<Time> | undefined) => {
        if (!candleSeriesRef.current) return;

        const getBarData = () => {
          if (!datafeedRef.current) return null;

          const data = datafeedRef.current.getData();
          if (data.candleData.length < 2) return null; // 최초렌더링시에 웹소켓 데이터가 먼저 들어오는 경우 데이터가 1개일 수 있다.

          const lastCandle = data.candleData[data.candleData.length - 1];
          const befLastCandle = data.candleData[data.candleData.length - 2];

          return {
            // time: lastCandle.time,
            open: lastCandle.open.toFixed(2),
            high: lastCandle.high.toFixed(2),
            low: lastCandle.low.toFixed(2),
            close: lastCandle.close.toFixed(2),
            changes: (befLastCandle.close - lastCandle.close).toFixed(2),
            percentage: (
              ((befLastCandle.close - lastCandle.close) / befLastCandle.close) *
              100
            ).toFixed(2),
          };
        };

        const isMobile = window.innerWidth <= 768; // Common breakpoint for mobile
        // 범례 텍스트 셋팅
        const setLegendText = ({
          open,
          high,
          low,
          close,
          changes,
          percentage,
        }: {
          open: string;
          high: string;
          low: string;
          close: string;
          changes: string;
          percentage: string;
        }) => {
          if (legendRef.current) {
            legendRef.current.innerHTML = `
        <div style="position: absolute; 
                  left: 12px; 
                  top: 12px; 
                  z-index: 10; 
                  font-size: ${isMobile ? "8px" : "14px"}; 
                  font-family: Pretendard Variable !important;  
                  font-weight: 300; 
                  display: flex;
                  flex-direction: ${isMobile ? "column" : "row"};
                  align-items: ${isMobile ? "flex-start" : "center"};
                  gap: ${isMobile ? "4px" : "8px"};
                  color: #ccc;">
        <span>${exchange1}:${symbol}_KRW/${exchange2}:${symbol}_USDT.P</span>
        ${
          isMobile
            ? `<div style="display: flex; align-items: center; gap: 4px;">
            <span style="color: #00c16e;">O ${open}</span>
            <span style="color: #00c16e;">H ${high}</span>
            <span style="color: #00c16e;">L ${low}</span>
            <span style="color: #00c16e;">C ${close}</span>
            <span style="color: #00c16e; font-weight: bold;">${
              parseFloat(changes) > 0 ? "+" + changes : "-" + changes
            } (${
              parseFloat(percentage) > 0 ? "+" + percentage : "-" + percentage
            }%)</span>
          </div>`
            : `<span style="color: #00c16e;">O ${open}</span>
           <span style="color: #00c16e;">H ${high}</span>
           <span style="color: #00c16e;">L ${low}</span>
           <span style="color: #00c16e;">C ${close}</span>
           <span style="color: #00c16e; font-weight: bold;">${
             parseFloat(changes) > 0 ? "+" + changes : "-" + changes
           } (${
             parseFloat(percentage) > 0 ? "+" + percentage : "-" + percentage
           }%)</span>`
        }
      </div>
      `;
          }
        };

        const validCrosshairPoint =
          (param?.seriesData?.size ?? 0 > 0) ? true : false;

        let barData;
        // let time

        if (validCrosshairPoint) {
          if (!param) return;

          const currentBar = param.seriesData.get(candleSeriesRef.current);
          if (!isBarData(currentBar)) return;

          const previousBar = param.logical
            ? candleSeriesRef.current.dataByIndex(param.logical - 1)
            : undefined;
          if (!isBarData(previousBar)) return;

          barData = {
            // time: currentBar.time,
            open: currentBar.open.toFixed(2),
            high: currentBar.high.toFixed(2),
            low: currentBar.low.toFixed(2),
            close: currentBar.close.toFixed(2),
            changes: (previousBar.close - currentBar.close).toFixed(2),
            percentage: (
              ((previousBar.close - currentBar.close) / previousBar.close) *
              100
            ).toFixed(2),
          };

          // time = new Date(barData.time * 1000).toUTCString()
        } else {
          // 웹소켓 데이터가 들어오지 않았을 때, 차트에 있는 마지막 봉 데이터를 가져옴
          barData = getBarData(); // bar.time이 datafeedRef에서 가져온 거라 브라우저시간에 아직 조정전임
          if (!barData) return;
          // time = new Date(barData.time * 1000).toLocaleString() // 알아서 브라우저 시간에 맞게끔 변환됨
        }

        setLegendText(barData);
      },
      [symbol, exchange1, exchange2]
    );

    // CSR 기반 fetcher 대체 함수: 기존 Remix fetcher.submit 대체
    const fetchCandles = useCallback(
      async (params: Record<string, unknown>) => {
        setCandleFetcherState("loading");
        setCandleFetcherError(null);
        try {
          const query = new URLSearchParams(
            params as Record<string, string>
          ).toString();
          const response = await fetch(`/api/kline?${query}`, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          });
          if (!response.ok) throw new Error("Network error");
          const data = await response.json();
          setCandleFetcherData(data);
        } catch (err) {
          setCandleFetcherError(err);
        } finally {
          setCandleFetcherState("idle");
        }
      },
      []
    );

    // 거래소1, 2 캔들 데이터를 조합하여 차트에 업데이트하는 함수
    const handleCombinedKline = useCallback(
      (data1: CandleBarData, data2: CandleBarData) => {
        if (
          !chartRef.current ||
          !candleSeriesRef.current ||
          !volumeSeriesRef.current ||
          !datafeedRef.current
        ) {
          return;
        }

        // Series에 업데이트할 때는 브라우저 타임존 오프셋을 고려해서 시간을 조정해야 정상적으로 브라우저시간으로 출력된다.
        // todo : 굳이 브라우저 시간 가져오는 메소드 사용하지 않고, toLocaleString()으로 바로 변환해도 될듯
        const time =
          Math.floor(data1.time / 1000) + getBrowserTimezoneOffset() * 60 * 60;

        const candle: CandlestickData = {
          time: time as Time,
          open: Number((data1.open / data2.open).toFixed(2)),
          high: Number((data1.high / data2.high).toFixed(2)),
          low: Number((data1.low / data2.low).toFixed(2)),
          close: Number((data1.close / data2.close).toFixed(2)),
        };
        const volume: HistogramData = {
          time: time as Time,
          value: data1.volume + data2.volume,
        };
        const ex1VolumeData: HistogramData = {
          time: time as Time,
          value: data1.volume,
        };

        const ex2VolumeData: HistogramData = {
          time: time as Time,
          value: data2.volume,
        };

        const candleDataUpdate = () => {
          // 현재 시리즈의 데이터 배열
          const seriesData = datafeedRef.current?.getData().candleData ?? [];
          // 가장 오래된 데이터의 time
          const oldestTime =
            seriesData.length > 0 ? seriesData[0].time : undefined;

          const candleTimeValue = getTimeValue(candle.time);
          const oldestTimeValue = getTimeValue(oldestTime);

          if (
            typeof candleTimeValue === "number" &&
            typeof oldestTimeValue === "number" &&
            candleTimeValue < oldestTimeValue
          ) {
            return;
          }
          if (
            !chartRef.current ||
            !candleSeriesRef.current ||
            !volumeSeriesRef.current
          )
            return;

          // 해당 time에 이미 데이터가 있는지 확인
          // const existingCandle =
          //   typeof candle.time !== "undefined" &&
          //   datafeedRef.current
          //     ?.getData()
          //     .candleData.some((d) => d.time === candle.time);
          // const historicalUpdate = !!existingCandle;

          try {
            candleSeriesRef.current.update(candle, true);
            volumeSeriesRef.current.update(
              {
                ...volume,
                color: candle.close > candle.open ? "#00CE84" : "#FC2861",
              },
              true
            );
            volumeSeriesEx1Ref.current?.update(
              {
                ...ex1VolumeData,
                color: candle.close > candle.open ? "#00CE84" : "#FC2861",
              },
              true
            );
            volumeSeriesEx2Ref.current?.update(
              {
                ...ex2VolumeData,
                color: candle.close > candle.open ? "#00CE84" : "#FC2861",
              },
              true
            );
          } catch {
            // fallback: 항상 false로 update
            candleSeriesRef.current.update(candle, false);
            volumeSeriesRef.current.update(
              {
                ...volume,
                color: candle.close > candle.open ? "#00CE84" : "#FC2861",
              },
              false
            );
            volumeSeriesEx1Ref.current?.update(
              {
                ...ex1VolumeData,
                color: candle.close > candle.open ? "#00CE84" : "#FC2861",
              },
              false
            );
            volumeSeriesEx2Ref.current?.update(
              {
                ...ex2VolumeData,
                color: candle.close > candle.open ? "#00CE84" : "#FC2861",
              },
              false
            );
          }
        };

        candleDataUpdate();

        const currentData = datafeedRef.current.getData();
        if (!currentData) return;

        // datafeedRef에 업데이트 할 때에는 브라우저 시간 고려하지 않고, 원래 시간대로 업데이트
        const adjustedTime =
          (time as number) - getBrowserTimezoneOffset() * 60 * 60;

        // 이미 존재하는 캔들인지 확인
        const existingCandleIndex = currentData.candleData.findIndex(
          (c) => c.time === adjustedTime
        );

        // 기존 캔들 업데이트
        if (existingCandleIndex !== -1) {
          const updatedCandleData = [...currentData.candleData];
          const updatedVolumeData = [...currentData.volumeData];
          const updatedEx1VolumeData = [...(currentData.ex1VolumeData ?? [])];
          const updatedEx2VolumeData = [...(currentData.ex2VolumeData ?? [])];
          const usdtCandleData = currentData.usdtCandleData ?? [];

          updatedCandleData[existingCandleIndex] = {
            ...candle,
            time: adjustedTime,
          };
          updatedVolumeData[existingCandleIndex] = {
            ...volume,
            time: adjustedTime,
          };
          updatedEx1VolumeData[existingCandleIndex] = {
            ...updatedEx1VolumeData[existingCandleIndex],
            time: adjustedTime,
          };
          updatedEx2VolumeData[existingCandleIndex] = {
            ...updatedEx2VolumeData[existingCandleIndex],
            time: adjustedTime,
          };
          usdtCandleData[existingCandleIndex] = {
            ...usdtCandleData[existingCandleIndex],
            time: adjustedTime,
          };

          datafeedRef.current.setData({
            candleData: updatedCandleData,
            volumeData: updatedVolumeData,
            ex1VolumeData: updatedEx1VolumeData,
            ex2VolumeData: updatedEx2VolumeData,
            usdtCandleData,
          });
        }
        // 새로운 캔들 추가
        else {
          datafeedRef.current.setData({
            candleData: [
              ...currentData.candleData,
              { ...candle, time: adjustedTime },
            ].sort((a, b) => a.time - b.time),
            volumeData: [
              ...currentData.volumeData,
              { ...volume, time: adjustedTime },
            ].sort((a, b) => a.time - b.time),
            ex1VolumeData: [
              ...(currentData.ex1VolumeData ?? []),
              {
                ...ex1VolumeData,
                time: adjustedTime,
              },
            ].sort((a, b) => a.time - b.time),
            ex2VolumeData: [
              ...(currentData.ex2VolumeData ?? []),
              {
                ...ex2VolumeData,
                time: adjustedTime,
              },
            ].sort((a, b) => a.time - b.time),
          });
        }

        const adjusted_renewedData =
          datafeedRef.current.adjustDataByBrowserTimezone(
            datafeedRef.current.getData()
          );

        if (macdSeriesRef.current) {
          // 브라우저 타임존 오프셋을 고려해서 시간을 조정
          const macdInput = {
            values: adjusted_renewedData.candleData.map(
              (candle) => candle.close
            ),
            fastPeriod: 12,
            slowPeriod: 26,
            signalPeriod: 9,
            SimpleMAOscillator: false,
            SimpleMASignal: false,
          };
          const macdData = MACD.calculate(macdInput);
          const macdHistogramData: HistogramData[] = macdData.map(
            (macd, index) => ({
              time: adjusted_renewedData.candleData[index + 25].time as Time,
              value: macd.histogram ? macd.histogram : 0,
            })
          );
          macdSeriesRef.current.setData(macdHistogramData);
        }

        if (rsiSeriesRef.current) {
          const rsiInput = {
            values: adjusted_renewedData.candleData.map(
              (candle) => candle.close
            ),
            period: 14,
          };
          const rsiData = RSI.calculate(rsiInput);
          const rsiLineData: LineData[] = rsiData.map((rsi, index) => ({
            time: adjusted_renewedData.candleData[index + 13].time as Time,
            value: rsi,
          }));
          rsiSeriesRef.current.setData(rsiLineData);
        }

        // 범례 업데이트 : 차트에 커서가 없을 때만 업데이트
        if (!crosshairVisibleRef.current) updateLegend(undefined);
      },
      [updateLegend]
    );

    // 거래소1 메시지 핸들러
    const handleExchange1Message = useCallback(
      (data: CandleBarData | TickerData | PositionData) => {
        if (!datafeedRef.current) return;
        if (!isCandleBarData(data)) return;

        // USDT 캔들 데이터는 라인 시리즈 및 데이터피드에 반영
        if ((data as CandleBarData).symbol === "USDT") {
          const time =
            Math.floor(data.time / 1000) + getBrowserTimezoneOffset() * 60 * 60;
          try {
            if (lineSeriesRef.current) {
              lineSeriesRef.current.update(
                {
                  time: time as Time,
                  value: data.close,
                },
                true
              );
            }
          } catch {
            if (lineSeriesRef.current) {
              lineSeriesRef.current.update(
                {
                  time: time as Time,
                  value: data.close,
                },
                false
              );
            }
          }
          try {
            // 데이터피드에도 반영
            if (datafeedRef.current) {
              const currentData = datafeedRef.current.getData();
              const usdtCandleData = currentData.usdtCandleData;
              if (!usdtCandleData) return;
              const idx = usdtCandleData.findIndex(
                (c) => c && typeof c.time !== "undefined" && c.time === time
              );
              if (idx !== -1) {
                usdtCandleData[idx] = {
                  time: Number(Math.floor(data.time / 1000)),
                  value: data.close,
                };
              } else {
                usdtCandleData.push({
                  time: Number(Math.floor(data.time / 1000)),
                  value: data.close,
                });
              }
              datafeedRef.current.setData({
                ...currentData,
                usdtCandleData: usdtCandleData,
              });
            }
          } catch (error) {
            console.log(time);
            console.error("Error updating USDT line series:", error);
          }
          return;
        }

        // 동일한 time의 데이터가 이미 있으면 기존 데이터를 꺼내서 value를 업데이트하고 버퍼에 다시 저장
        klineBuffer1.current.set(data.time, data);

        // 두 거래소 모두 해당 time 데이터가 있으면 조합
        const data2 = klineBuffer2.current.get(data.time);
        if (data2) {
          handleCombinedKline(data as CandleBarData, data2 as CandleBarData);
        }
      },
      [handleCombinedKline, exchange2, symbol]
    );

    // 거래소2 메시지 핸들러
    const handleExchange2Message = useCallback(
      (data: CandleBarData | TickerData | PositionData) => {
        if (!datafeedRef.current) return;
        if (!isCandleBarData(data)) return;

        if (exchange2 === "GATEIO") {
          const contractKey = `${symbol}_USDT` as keyof typeof ContractSize;
          if (contractKey in ContractSize) {
            data.volume = data.volume * ContractSize[contractKey];
          }
        }

        // 버퍼에 저장
        klineBuffer2.current.set(data.time, data);

        // 두 거래소 모두 해당 time 데이터가 있으면 조합
        const data1 = klineBuffer1.current.get(data.time);
        if (data1) {
          handleCombinedKline(data1, data);
        }
      },
      [handleCombinedKline, exchange2, symbol]
    );

    // 차트 초기화
    useEffect(() => {
      if (!chartContainerRef.current) return;

      lastFetchTypeRef.current = "initial";
      lastHistoricalTimeRef.current = null;
      errorCountRef.current = 0;

      // interval이 변경되었는지 확인
      if (currentIntervalRef.current !== interval) {
        intervalChangeRef.current = true;
        currentIntervalRef.current = interval;
      } else {
        intervalChangeRef.current = false;
      }

      // symbol이 변경되었는지 확인
      if (currentSymbolRef.current !== symbol) {
        symbolChangeRef.current = true;
        currentSymbolRef.current = symbol;
      } else {
        symbolChangeRef.current = false;
      }

      const chartContainer = chartContainerRef.current;

      chartRef.current = createChart(chartContainerRef.current, {
        layout: {
          background: { color: "#1E1A24" },
          textColor: "#DDD",
          panes: {
            separatorColor: "rgb(111, 91, 143)",
            separatorHoverColor: "rgba(255, 0, 0, 0.1)",
            // setting this to false will disable the resize of the panes by the user
            enableResize: true,
          },
        },
        grid: {
          vertLines: { color: "transparent" }, // 세로 그리드 라인 제거
          horzLines: { color: "transparent" }, // 가로 그리드 라인 제거
        },
        width: chartContainerRef.current.clientWidth,
        height: 640,
        timeScale: {
          timeVisible: true, // 시간을 표시
          borderVisible: true,
          secondsVisible: false, // 초는 제외
        },
        rightPriceScale: {
          visible: true,
          // scaleMargins: {
          //   top: 0.4,
          // },
        },
        leftPriceScale: {
          visible: false,
        },
        crosshair: {
          mode: 0, // This mode allows crosshair to move freely on the chart.
        },
      });
      const isMobile = window.innerWidth <= 768; // Common breakpoint for mobile

      // 워터마크 추가
      createImageWatermark(chartRef.current.panes()[0], "/ultimate-logo.png", {
        alpha: 0.3,
        maxHeight: chartContainerRef.current.clientWidth * 0.1,
        maxWidth: chartContainerRef.current.clientWidth * 0.1,
      });

      // 모바일에서 잘 동작하도록 pointermove -> mousemove이벤트로 전환해주는 핸들러
      const pointerMoveHandler = (e: PointerEvent) => {
        if (e.pointerType === "mouse") return;
        e.preventDefault();
        const mouseEvent = new MouseEvent("mousemove", {
          bubbles: true,
          cancelable: true,
          clientX: e.clientX,
          clientY: e.clientY,
          screenX: e.screenX,
          screenY: e.screenY,
          ctrlKey: e.ctrlKey,
          shiftKey: e.shiftKey,
          altKey: e.altKey,
          metaKey: e.metaKey,
          button: e.button,
          buttons: e.buttons,
          relatedTarget: e.relatedTarget,
        });
        chartContainer.dispatchEvent(mouseEvent);
      };

      chartContainer.addEventListener("pointermove", pointerMoveHandler, {
        passive: false,
      });

      // 범례(legend) 초기화
      const initializeLegend = () => {
        const legend = document.createElement("div");

        legend.innerHTML = `
        <div style="position: absolute; 
                  left: 12px; 
                  top: 12px; 
                  z-index: 10; 
                  font-size: ${isMobile ? "8px" : "14px"}; 
                  font-family: Pretendard Variable;  
                  font-weight: 300; 
                  display: flex;
                  flex-direction: ${isMobile ? "column" : "row"};
                  align-items: ${isMobile ? "flex-start" : "center"};
                  gap: ${isMobile ? "4px" : "8px"};
                  color: #ccc;">
          <span>${exchange1}:${symbol}_KRW/${exchange2}:${symbol}_USDT.P</span>
          ${
            isMobile
              ? `<div style="display: flex; align-items: center; gap: 4px;">
              <span style="color: #00c16e;">O 0.0000000</span>
              <span style="color: #00c16e;">H 0.0000000</span>
              <span style="color: #00c16e;">L 0.0000000</span>
              <span style="color: #00c16e;">C 0.0000000</span>
              <span style="color: #00c16e; font-weight: bold;">+0.0000000 (+0.00%)</span>
            </div>`
              : `<span style="color: #00c16e;">O 0.0000000</span>
             <span style="color: #00c16e;">H 0.0000000</span>
             <span style="color: #00c16e;">L 0.0000000</span>
             <span style="color: #00c16e;">C 0.0000000</span>
             <span style="color: #00c16e; font-weight: bold;">+0.0000000 (+0.00%)</span>`
          }
        </div>
      `;
        chartContainerRef.current?.appendChild(legend);
        legendRef.current = legend;
      };

      initializeLegend();

      const crosshairHandler: MouseEventHandler<Time> = (
        param: MouseEventParams<Time>
      ) => {
        crosshairVisibleRef.current = param.seriesData.size > 0;
        updateLegend(param);
      };

      // 커서움직임에 따라 범례(legend) 업데이트
      chartRef.current.subscribeCrosshairMove(crosshairHandler);

      // 수직 축(border) 색상 설정
      chartRef.current.priceScale("right").applyOptions({
        borderColor: "#6F5B8F",
      });

      // 수평 축(border) 색상 설정
      chartRef.current.timeScale().applyOptions({
        borderColor: "#6F5B8F",
      });

      // 캔들스틱 시리즈 추가
      candleSeriesRef.current = chartRef.current.addSeries(CandlestickSeries, {
        upColor: "#00CE84",
        downColor: "#FC2861",
      });

      // 거래량 시리즈 추가
      volumeSeriesRef.current = chartRef.current.addSeries(
        HistogramSeries,
        {
          color: "#00CE84",
          priceFormat: {
            type: "volume",
          },
          priceScaleId: "",
        },
        1
      );
      volumeSeriesRef.current.moveToPane(1); // 거래량 시리즈를 별도의 Pane으로 이동

      // 거래소1 거래량 시리즈 추가
      volumeSeriesEx1Ref.current = chartRef.current.addSeries(
        HistogramSeries,
        {
          color: "#FFB347",
          priceFormat: {
            type: "volume",
          },
          priceScaleId: "",
        },
        2
      );
      volumeSeriesEx1Ref.current.moveToPane(2);

      // 거래소2 거래량 시리즈 추가
      volumeSeriesEx2Ref.current = chartRef.current.addSeries(
        HistogramSeries,
        {
          color: "#6495ED",
          priceFormat: {
            type: "volume",
          },
          priceScaleId: "",
        },
        3
      );
      volumeSeriesEx2Ref.current.moveToPane(3);

      // USDT 가격을 표시하기 위한 라인 시리즈 추가
      lineSeriesRef.current = chartRef.current.addSeries(LineSeries, {
        color: "#2962FF",
      });

      // 거래량 시리즈의 scaleMargin 조정
      volumeSeriesRef.current.priceScale().applyOptions({
        scaleMargins: {
          top: 0.4,
          bottom: 0,
        },
      });

      // 반응형 차트 크기 조정
      const resizeObserver = new ResizeObserver((entries) => {
        if (!entries.length) return;

        const chart = chartRef.current;
        const container = chartContainerRef.current;

        // no chart or DOM node? stop observing
        if (!chart || !container || !container.isConnected) {
          resizeObserver.disconnect();
          return;
        }

        const { width, height } = entries[0].contentRect;
        try {
          chart.applyOptions({ width, height });
          volumeSeriesRef.current?.getPane()?.setStretchFactor(1);
          volumeSeriesEx1Ref.current?.getPane()?.setStretchFactor(1);
          volumeSeriesEx2Ref.current?.getPane()?.setStretchFactor(1);
        } catch {
          resizeObserver.disconnect();
        }
      });

      resizeObserver.observe(chartContainerRef.current);

      setInitialFetchCompleted(false);

      // 캔들 데이터를 가져오기 위한 데이터피드 생성
      datafeedRef.current = new CandleDatafeed(exchange1, symbol, interval);

      // Refs 초기화
      candleSeriesRef.current?.setData([]);
      volumeSeriesRef.current?.setData([]);
      volumeSeriesEx1Ref.current?.setData([]);
      volumeSeriesEx2Ref.current?.setData([]);
      lineSeriesRef.current?.setData([]);

      // 캔들 데이터 가져오기 (CSR fetch)
      fetchCandles({
        exchanges: [exchange1, exchange2],
        symbol,
        interval,
      });

      // 마지막 봉 시간을 정확히 가져오기 위한 함수
      const getExactMaxLogicalCandleTime = () => {
        if (!chartRef.current) return;

        const range = chartRef.current.timeScale().getVisibleRange();
        const lastBarTime = range?.to;
        if (!lastBarTime) return;

        // 좌표로 먼저 변환해야지 정확한 논리값을 가져올 수 있음
        const lastBarCoordinate = chartRef.current
          .timeScale()
          .timeToCoordinate(lastBarTime);
        if (!lastBarCoordinate) return;

        const lastBarLogical = chartRef.current
          .timeScale()
          .coordinateToLogical(lastBarCoordinate);
        if (!lastBarLogical) return;

        return lastBarLogical;
      };

      // 차트 오른쪽에 whitespace 데이터 추가
      const addWhiteSpacesToRight = () => {
        if (!chartRef.current || !candleSeriesRef.current) return;

        const lastBarLogical = getExactMaxLogicalCandleTime();
        if (!lastBarLogical) return;

        const lastBarTimeCoordinate = chartRef.current
          .timeScale()
          .logicalToCoordinate(lastBarLogical);
        if (!lastBarTimeCoordinate) return;

        const lastBarTime = chartRef.current
          .timeScale()
          .coordinateToTime(lastBarTimeCoordinate);
        if (!lastBarTime) return;

        const logicalRange = chartRef.current
          .timeScale()
          .getVisibleLogicalRange();
        if (!logicalRange) return;

        for (let i = 1; i < logicalRange.to - lastBarLogical; i++) {
          candleSeriesRef.current.update({
            time: ((lastBarTime as number) +
              i * intervalInSeconds(interval)) as Time,
          });
        }
      };

      // 차트의 visibleLogicalRange가 변경될 때마다 호출되는 함수
      const visibleLogicalRangeChangeHandler: LogicalRangeChangeEventHandler = (
        logicalRange: LogicalRange | null
      ) => {
        if (!logicalRange) return;

        // visibleRange에 따라 whitespace 데이터 추가
        addWhiteSpacesToRight();

        // 왼쪽 봉이 10개 미만일 때 데이터 추가 요청 ~ 추후 개수 조정 가능
        if (logicalRange.from < 10) {
          // 현재 시간 확인
          const now = Date.now();

          // 1초 이내 중복 요청 방지 + 이미 로딩 중인지 확인
          if (now - lastRequestTimeRef.current < 1000 || isLoadingRef.current) {
            return;
          }
          lastRequestTimeRef.current = now;
          isLoadingRef.current = true;

          const earliestDataTime = datafeedRef.current?.getFirstDataTime();

          if (!earliestDataTime) return;

          // 현재 차트에서 보이는 최초 데이터 시간보다 interval 시간만큼 빼서 데이터를 가져오는데, 데이터 중복이 발생하지 않도록 조정
          const adjustedEarliestDataTime =
            earliestDataTime! - intervalInSeconds(interval);

          lastFetchTypeRef.current = "historical";
          lastHistoricalTimeRef.current = adjustedEarliestDataTime;

          // 봉 데이터를 가져오기 (CSR fetch)
          fetchCandles({
            exchanges: [exchange1, exchange2],
            symbol,
            interval,
            to: adjustedEarliestDataTime,
          });
        }
      };

      // infinite history loading
      // https://tradingview.github.io/lightweight-charts/tutorials/demos/infinite-history
      chartRef.current
        .timeScale()
        .subscribeVisibleLogicalRangeChange(visibleLogicalRangeChangeHandler);

      const onVisibilityChange = () => {
        if (!navigator.onLine) return;
        if (document.visibilityState === "visible") {
          // 1) 기존 데이터 클리어
          // datafeedRef.current?.setData({
          //   candleData: [],
          //   volumeData: [],
          //   ex1VolumeData: [],
          //   ex2VolumeData: [],
          //   usdtCandleData: [],
          // });
          // candleSeriesRef.current?.setData([]);
          // volumeSeriesRef.current?.setData([]);
          // volumeSeriesEx1Ref.current?.setData([]);
          // volumeSeriesEx2Ref.current?.setData([]);
          // lineSeriesRef.current?.setData([]);

          // 2) 재요청
          setTimeout(() => {
            fetchCandles({
              exchanges: [exchange1, exchange2],
              symbol,
              interval,
            });
          }, 150);
        }
      };

      document.addEventListener("visibilitychange", onVisibilityChange);

      const clickHandler = (param: MouseEventParams<Time>) => {
        if (
          isAdminRoute &&
          param.point &&
          chartRef.current &&
          candleSeriesRef.current
        ) {
          const barPrice = candleSeriesRef.current.coordinateToPrice(
            param.point.y
          );
          if (barPrice !== null) {
            setClickedPrice(barPrice);
          }
        }
      };

      if (isAdminRoute && chartRef.current) {
        chartRef.current.subscribeClick(clickHandler);
      }

      return () => {
        chartContainer.removeEventListener("pointermove", pointerMoveHandler);
        document.removeEventListener("visibilitychange", onVisibilityChange);
        resizeObserver.disconnect();
        if (legendRef.current && chartContainer) {
          chartContainer.removeChild(legendRef.current);
        }
        chartRef.current?.unsubscribeCrosshairMove(crosshairHandler);
        if (isAdminRoute && chartRef.current) {
          chartRef.current.unsubscribeClick(clickHandler);
        }
        chartRef.current
          ?.timeScale()
          .unsubscribeVisibleLogicalRangeChange(
            visibleLogicalRangeChangeHandler
          );
        chartRef.current?.remove();
        chartRef.current = null;
        datafeedRef.current = null;
        candleSeriesRef.current = null;
        volumeSeriesRef.current = null;
      };
      // useFetcher로 인한 무한 렌더링 방지
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [exchange1, exchange2, symbol, interval, updateLegend]);

    // 실시간 캔들 데이터 수신을 위한 useEffect (웹소켓 메시지 리스너 등록)
    useEffect(() => {
      if (!addMessageListener1 || !removeMessageListener1) return;

      addMessageListener1(handleExchange1Message);
      addMessageListener2(handleExchange2Message);
      return () => {
        removeMessageListener1(handleExchange1Message);
        removeMessageListener2(handleExchange2Message);
      };
    }, [
      addMessageListener1,
      removeMessageListener1,
      addMessageListener2,
      removeMessageListener2,
      handleExchange1Message,
      handleExchange2Message,
    ]);

    // 캔들 데이터를 fetcher 비동기 처리 후, 차트에 데이터를 업데이트
    useEffect(() => {
      if (
        !chartRef.current ||
        !candleSeriesRef.current ||
        !volumeSeriesRef.current ||
        !volumeSeriesEx1Ref.current ||
        !volumeSeriesEx2Ref.current ||
        !lineSeriesRef.current ||
        !datafeedRef.current
      )
        return;

      if (candleFetcherState !== "idle" || !candleFetcherData) return;

      // 인터벌 변경시에 발동되는 useEffect는 무시
      if (intervalChangeRef.current) {
        intervalChangeRef.current = false;
        return;
      }

      // 심볼 변경시에 발동되는 useEffect는 무시
      if (symbolChangeRef.current) {
        symbolChangeRef.current = false;
        return;
      }

      isLoadingRef.current = false;

      // 에러가 발생한 경우 재시도
      if (candleFetcherError) {
        // 간단한 재시도 로직 (3회 제한 등은 필요시 추가)
        setTimeout(() => {
          fetchCandles({
            exchanges: [exchange1, exchange2],
            symbol: symbol,
            interval: interval,
          });
        }, 1000);
        return;
      }
      const data = candleFetcherData as CandleData;

      const originalData = datafeedRef.current.getData() || {
        candleData: [],
        volumeData: [],
        ex1VolumeData: [],
        ex2VolumeData: [],
        usdtCandleData: [],
      };

      const candleDataMap = new Map<number, CandlestickData>();
      [...data.candleData, ...originalData.candleData].forEach((candle) => {
        candleDataMap.set(candle.time as number, candle as CandlestickData);
      });

      const volumeDataMap = new Map<number, HistogramData>();
      [...data.volumeData, ...originalData.volumeData].forEach((volume) => {
        const correspondingCandle = candleDataMap.get(volume.time as number);
        const color =
          correspondingCandle &&
          correspondingCandle.close > correspondingCandle.open
            ? "#00CE84"
            : "#FC2861";
        volumeDataMap.set(
          volume.time as number,
          { ...volume, color } as HistogramData
        );
      });

      const ex1VolumeDataMap = new Map<number, HistogramData>();
      [
        ...(data.ex1VolumeData ?? []),
        ...(originalData.ex1VolumeData ?? []),
      ].forEach((volume) => {
        const correspondingCandle = candleDataMap.get(volume.time as number);
        const color =
          correspondingCandle &&
          correspondingCandle.close > correspondingCandle.open
            ? "#00CE84"
            : "#FC2861";
        ex1VolumeDataMap.set(
          volume.time as number,
          { ...volume, color } as HistogramData
        );
      });

      const ex2VolumeDataMap = new Map<number, HistogramData>();
      [
        ...(data.ex2VolumeData ?? []),
        ...(originalData.ex2VolumeData ?? []),
      ].forEach((volume) => {
        const correspondingCandle = candleDataMap.get(volume.time as number);
        const color =
          correspondingCandle &&
          correspondingCandle.close > correspondingCandle.open
            ? "#00CE84"
            : "#FC2861";
        ex2VolumeDataMap.set(
          volume.time as number,
          { ...volume, color } as HistogramData
        );
      });

      const usdtCandleDataMap = new Map<number, LineData>();
      [
        ...(data.usdtCandleData ?? []),
        ...(originalData.usdtCandleData ?? []),
      ].forEach((candle) => {
        if (!candle || typeof candle.time === "undefined") return;
        usdtCandleDataMap.set(candle.time as number, candle as LineData);
      });

      const candleData = Array.from(candleDataMap.values()).sort(
        (a, b) => Number(a.time) - Number(b.time)
      );
      const volumeData = Array.from(volumeDataMap.values()).sort(
        (a, b) => Number(a.time) - Number(b.time)
      );
      const ex1VolumeData = Array.from(ex1VolumeDataMap.values()).sort(
        (a, b) => Number(a.time) - Number(b.time)
      );
      const ex2VolumeData = Array.from(ex2VolumeDataMap.values()).sort(
        (a, b) => Number(a.time) - Number(b.time)
      );
      const usdtCandleData = Array.from(usdtCandleDataMap.values()).sort(
        (a, b) => Number(a.time) - Number(b.time)
      );
      const renewedData = {
        candleData,
        volumeData,
        ex1VolumeData,
        ex2VolumeData,
        usdtCandleData,
      } as CandleData;

      if (!renewedData.candleData.length || !renewedData.volumeData.length) {
        return;
      }

      // 데이터피드에 데이터를 업데이트
      datafeedRef.current.setData(renewedData);

      // 브라우저 타임존 오프셋을 고려해서 시간을 조정
      const adjusted_renewedData =
        datafeedRef.current.adjustDataByBrowserTimezone(renewedData);

      candleSeriesRef.current.setData(
        adjusted_renewedData.candleData as CandlestickData[]
      );
      volumeSeriesRef.current.setData(
        adjusted_renewedData.volumeData as HistogramData[]
      );
      volumeSeriesEx1Ref.current.setData(
        adjusted_renewedData.ex1VolumeData as HistogramData[]
      );
      volumeSeriesEx2Ref.current.setData(
        adjusted_renewedData.ex2VolumeData as HistogramData[]
      );
      lineSeriesRef.current.setData(
        adjusted_renewedData.usdtCandleData as LineData[]
      );

      if (macdSeriesRef.current) {
        // 브라우저 타임존 오프셋을 고려해서 시간을 조정
        const macdInput = {
          values: adjusted_renewedData.candleData.map((candle) => candle.close),
          fastPeriod: 12,
          slowPeriod: 26,
          signalPeriod: 9,
          SimpleMAOscillator: false,
          SimpleMASignal: false,
        };
        const macdData = MACD.calculate(macdInput);
        const macdHistogramData: HistogramData[] = macdData.map(
          (macd, index) => ({
            time: adjusted_renewedData.candleData[index + 25].time as Time,
            value: macd.histogram ? macd.histogram : 0,
          })
        );
        macdSeriesRef.current.setData(macdHistogramData);
      }

      // RSI 계산 및 업데이트
      if (rsiSeriesRef.current) {
        const rsiInput = {
          values: adjusted_renewedData.candleData.map((candle) => candle.close),
          period: 14,
        };
        const rsiData = RSI.calculate(rsiInput);
        const rsiLineData: LineData[] = rsiData.map((rsi, index) => ({
          time: adjusted_renewedData.candleData[index + 13].time as Time,
          value: rsi,
        }));
        rsiSeriesRef.current.setData(rsiLineData);
      }

      // 범례 업데이트
      if (!crosshairVisibleRef.current) updateLegend(undefined);

      // 최초 데이터 fetch 완료 시에만 데이터 개수에 맞게 꽉 차게 차트 크기 조정
      if (!initialFetchCompleted) {
        chartRef.current.timeScale().fitContent();
        setInitialFetchCompleted(true);
      }
    }, [
      candleFetcherState,
      candleFetcherData,
      candleFetcherError,
      exchange1,
      exchange2,
      interval,
      symbol,
      initialFetchCompleted,
      updateLegend,
      fetchCandles,
    ]);

    // 포지션 데이터가 변경될 때마다 차트에 포지션 표시
    useEffect(() => {
      if (!positions || !candleSeriesRef.current) return;

      // 포지션들 중 현재 차트 심볼만 필터링
      const filteredPositions = positions.filter(
        (item) => item.contract === symbol
      );

      const priceLines: Array<IPriceLine> = [];
      const markersInstances: Array<ISeriesMarkersPluginApi<Time>> = [];

      filteredPositions.forEach((pos) => {
        // 가격선 그리기
        const entryPrice = Number(pos.entryPrice);
        const pnl = Number(pos.unrealisedPnl);
        const title = pnl > 0 ? `+${pnl.toFixed(2)}` : pnl.toFixed(2);
        const priceLine = candleSeriesRef.current!.createPriceLine({
          price: entryPrice,
          color: "#FFA500",
          lineWidth: 2,
          lineStyle: 1, // Dotted
          axisLabelVisible: true,
          title,
        });
        priceLines.push(priceLine);

        // 마커 표시
        const timeValue =
          typeof pos.openTime === "number"
            ? pos.openTime
            : new Date(pos.openTime!).getTime() / 1000;
        const adjustedTime = alignTimeToInterval(timeValue, interval) as Time;
        const timeWithTZ = ((adjustedTime as number) +
          getBrowserTimezoneOffset() * 3600) as Time;

        const marker = createSeriesMarkers(candleSeriesRef.current!, [
          {
            time: timeWithTZ,
            position: pos.size! > 0 ? "belowBar" : "aboveBar",
            color: pos.size! > 0 ? "#22AB94" : "#F7525F",
            shape: pos.size! > 0 ? "arrowUp" : "arrowDown",
            text: pos.size! > 0 ? "LONG" : "SHORT",
          },
        ]);
        markersInstances.push(marker);
      });

      return () => {
        priceLines.forEach((priceLine) => {
          candleSeriesRef.current?.removePriceLine(priceLine);
        });
        if (candleSeriesRef.current) {
          markersInstances.forEach((marker) => {
            try {
              marker.detach();
            } catch {
              // chart가 dispose 된 경우 에러 무시
            }
          });
        }
      };
    }, [positions, symbol, interval]);

    // 마커 변경을 감지하고 차트에 적용하는 useEffect 추가
    useEffect(() => {
      if (!candleSeriesRef.current || markers.length === 0) return;

      // 차트에 마커 생성
      const markersInstance = createSeriesMarkers(
        candleSeriesRef.current,
        markers
      );

      // 마커 변경 또는 컴포넌트 언마운트 시 정리
      return () => {
        markersInstance.detach();
      };
    }, [markers]);

    // MACD 시리즈 추가 및 업데이트
    useEffect(() => {
      if (
        !chartContainerRef.current ||
        !chartRef.current ||
        !datafeedRef.current
      )
        return;

      const macdPaneIdx = chartRef.current.panes().length;

      // MACD 시리즈 추가
      if (showMACD) {
        macdSeriesRef.current = chartRef.current.addSeries(HistogramSeries, {
          color: "#FF6F61",
          priceFormat: {
            type: "volume",
          },
          priceScaleId: "",
        });
        macdSeriesRef.current.moveToPane(macdPaneIdx); // MACD 시리즈를 별도의 Pane으로 이동
        macdPaneRef.current = chartRef.current.panes()[macdPaneIdx];
        macdPaneRef.current.setHeight(100);

        // 브라우저 타임존 오프셋을 고려해서 시간을 조정
        const adjusted_renewedData =
          datafeedRef.current.adjustDataByBrowserTimezone(
            datafeedRef.current.getData()
          );

        const macdInput = {
          values: adjusted_renewedData.candleData.map((candle) => candle.close),
          fastPeriod: 12,
          slowPeriod: 26,
          signalPeriod: 9,
          SimpleMAOscillator: false,
          SimpleMASignal: false,
        };
        const macdData = MACD.calculate(macdInput);
        const macdHistogramData: HistogramData[] = macdData.map(
          (macd, index) => ({
            time: adjusted_renewedData.candleData[index + 25].time as Time,
            value: macd.histogram ? macd.histogram : 0,
          })
        );
        macdSeriesRef.current.setData(macdHistogramData);
      } else {
        if (macdSeriesRef.current && macdPaneRef.current) {
          chartRef.current?.removePane(macdPaneRef.current.paneIndex());
          macdSeriesRef.current = null;
          macdPaneRef.current = null;
        }
      }
      chartRef.current.panes().forEach((pane) => {
        pane.setHeight(100);
      }); // 거래량 캔들스틱 차트 높이 조정 : 이렇게 안해주면 높이가 달라짐..
    }, [showMACD]);

    // RSI 시리즈 추가 및 업데이트
    useEffect(() => {
      if (
        !chartContainerRef.current ||
        !chartRef.current ||
        !datafeedRef.current
      )
        return;

      const rsiPaneIdx = chartRef.current.panes().length;

      // RSI 시리즈 추가
      if (showRSI) {
        rsiSeriesRef.current = chartRef.current.addSeries(LineSeries, {
          color: "#1E90FF",
          lineWidth: 2,
        });
        rsiSeriesRef.current.moveToPane(rsiPaneIdx); // RSI 시리즈를 별도의 Pane으로 이동
        rsiPaneRef.current = chartRef.current.panes()[rsiPaneIdx];
        rsiPaneRef.current.setHeight(100); // RSI Pane 높이 조정

        // 브라우저 타임존 오프셋을 고려해서 시간을 조정
        const adjusted_renewedData =
          datafeedRef.current!.adjustDataByBrowserTimezone(
            datafeedRef.current.getData()
          );

        const rsiInput = {
          values: adjusted_renewedData.candleData.map((candle) => candle.close),
          period: 14,
        };
        const rsiData = RSI.calculate(rsiInput);
        const rsiLineData: LineData[] = rsiData.map((rsi, index) => ({
          time: adjusted_renewedData.candleData[index + 13].time as Time,
          value: rsi,
        }));
        rsiSeriesRef.current.setData(rsiLineData);
      } else {
        if (rsiSeriesRef.current && rsiPaneRef.current) {
          chartRef.current?.removePane(rsiPaneRef.current.paneIndex());
          rsiSeriesRef.current = null;
          rsiPaneRef.current = null;
        }
      }
      chartRef.current.panes().forEach((pane) => pane.setHeight(100)); // 거래량 캔들스틱 차트 높이 조정 : 이렇게 안해주면 높이가 달라짐..
    }, [showRSI]);

    return (
      <div className="chart-content">
        {/* {chartRef.current && candleSeriesRef.current && (
            <ToolBox
              chart={chartRef.current}
              series={candleSeriesRef.current}
              showMACD={showMACD}
              setShowMACD={setShowMACD}
              showRSI={showRSI}
              setShowRSI={setShowRSI}
            />
          )} */}
        <section ref={chartContainerRef} className="chart-area" />
      </div>
    );
  }
);

CompTradingviewChart.displayName = "CompTradingviewChart";

export default CompTradingviewChart;
