import { useMemo, useEffect } from "react";
import { createWebSocketStore } from "../../states/chartState";
import TickerInfoBar from "./TickerInfoBar";
import CompTradingviewChart from "./CompTradingviewChart";
import TimeSelector from "./TimeSelectorBox";
import { useStore } from "zustand/react";

interface CompChartProps {
  exchange1: string;
  exchange2: string;
  symbol?: string;
  interval?: string;
}

export const CompChart = ({
  exchange1,
  exchange2,
  symbol,
  interval,
}: CompChartProps) => {
  const store1 = useMemo(
    () =>
      createWebSocketStore({
        exchange: exchange1,
        symbol,
        interval,
      }),
    [exchange1, symbol, interval]
  );
  const store2 = useMemo(
    () =>
      createWebSocketStore({
        exchange: exchange2,
        symbol,
        interval,
      }),
    [exchange2, symbol, interval]
  );

  useEffect(() => {
    store1.getState().connectWebSocket();
    store2.getState().connectWebSocket();
    return () => {
      store1.getState().disconnectWebSocket();
      store2.getState().disconnectWebSocket();
    };
  }, [store1, store2]);

  // 아래와 같이 스토어로부터 동기화를 시켜야 CompTradingviewChart에 매개변수로 전달해줘서 티커, 봉이 바뀔 때에 CompTradingviewChart가 리렌더링될 수 있다.
  const storeSymbol = useStore(store1, (state) => state.symbol);
  const storeInterval = useStore(store1, (state) => state.interval);

  return (
    <div
      className="chart-container"
      style={{ backgroundColor: "rgb(19, 18, 21)" }}
    >
      <TickerInfoBar
        exchange={exchange2}
        symbol={storeSymbol}
        store={store2}
        onSymbolChange={(newSymbol: string) => {
          store1.getState().setSymbol(newSymbol);
          store2.getState().setSymbol(newSymbol);
        }}
      />
      <div className="chart-wrapper">
        <TimeSelector
          store={store1}
          onIntervalChange={(newInterval) => {
            store1.getState().setInterval(newInterval);
            store2.getState().setInterval(newInterval);
          }}
        />
        <CompTradingviewChart
          store1={store1}
          store2={store2}
          symbol={storeSymbol}
          interval={storeInterval}
          exchange1={exchange1}
          exchange2={exchange2}
        />
      </div>
    </div>
  );
};

export default CompChart;
