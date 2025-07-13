import { useCallback, useEffect, useState } from "react";
import Select from "../shared/Select";
import { memo } from "react";
import type {
  CandleBarData,
  PositionData,
  TickerData,
} from "../../types/marketInfo";
import { useLocation } from "react-router-dom";
import type { CryptoOption } from "../../states/cryptoOptionState";
import { useCryptoOptionsStore } from "../../states/cryptoOptionState";
import { createWebSocketStore } from "../../states/chartState";

const TickerInfoBar = memo(
  ({
    store,
    exchange,
    onSymbolChange,
  }: {
    store: ReturnType<typeof createWebSocketStore>;
    exchange: string;
    onSymbolChange?: (newSymbol: string) => void;
  }) => {
    const { symbol, addMessageListener, removeMessageListener } =
      store.getState();
    const [tickerData, settickerData] = useState<TickerData>({
      change_percentage: null,
      funding_rate: null,
      index_price: null,
      mark_price: null,
    });
    const { cryptoOptions, addCryptoOption } = useCryptoOptionsStore();

    const location = useLocation();
    const isAdminRoute = location.pathname === "/admin";
    const [fetcherState, setFetcherState] = useState<
      "idle" | "loading" | "done"
    >("idle");
    const [fetcherData, setFetcherData] = useState<CryptoOption[] | null>(null);

    const formatNumber = (num: string | null, decimal: number) =>
      num !== null ? Number(num).toFixed(decimal) : "--";

    const priceChangeStatus =
      tickerData.change_percentage === null
        ? "neutral"
        : parseFloat(tickerData.change_percentage) > 0
        ? "positive"
        : parseFloat(tickerData.change_percentage) < 0
        ? "negative"
        : "neutral";

    const getFundingRateClass = (rate: number | null) => {
      if (rate === null || rate === 0) return "neutral";
      if (rate > 0) return "positive";
      return "negative";
    };

    const handleMessage = useCallback(
      (data: TickerData | CandleBarData | PositionData) => {
        if (data.channel === "futures.tickers") {
          data = data as TickerData;

          settickerData({
            change_percentage: data.change_percentage,
            funding_rate: data.funding_rate,
            mark_price: data.mark_price,
            index_price: data.index_price,
          });
        }
      },
      []
    );

    // 심볼 변경 시 스토어의 심볼 업데이트
    const handleSelectChange = useCallback(
      (option: CryptoOption) => {
        if (onSymbolChange) {
          onSymbolChange(option.value as string);
        }
      },
      [onSymbolChange]
    );

    useEffect(() => {
      addMessageListener(handleMessage);
      return () => {
        removeMessageListener(handleMessage);
      };
    }, [
      addMessageListener,
      removeMessageListener,
      handleMessage,
      symbol,
      exchange,
    ]);

    useEffect(() => {
      if (isAdminRoute && fetcherState === "idle") {
        setFetcherState("loading");
        fetch("/tickerInfo")
          .then((res) => res.json())
          .then((data) => {
            setFetcherData(data);
            setFetcherState("done");
          })
          .catch(() => {
            setFetcherData(null);
            setFetcherState("idle");
          });
      }
    }, [isAdminRoute, fetcherState]);

    useEffect(() => {
      if (
        fetcherState === "done" &&
        fetcherData &&
        Array.isArray(fetcherData)
      ) {
        addCryptoOption(fetcherData);
      }
    }, [fetcherData, fetcherState, addCryptoOption]);

    return (
      <div className="info-price">
        <Select
          options={cryptoOptions}
          selectedValue={symbol}
          name="cryptocurrency"
          classNames={{
            root: "crypto-select-box",
            dropdown: "crypto-options",
            option: "crypto-option",
          }}
          onChange={handleSelectChange}
        />
        <div className="border-bar" />
        <div className="price-container">
          <div className="price-wrapper">
            <span className="info-label">Mark</span>
            <span className="info-value">
              {formatNumber(tickerData.mark_price, 2)}
            </span>
          </div>
          <div className="price-wrapper">
            <span className="info-label">Index</span>
            <span className="info-value">
              {formatNumber(tickerData.index_price, 2)}
            </span>
          </div>
          <div className="change-status-display">
            <div className="status-wrapper">
              <span className="status-label"> 24H Change :</span>
              <span className={`status-value ${priceChangeStatus}`}>
                {formatNumber(tickerData.change_percentage, 2)}%
              </span>
            </div>
            <div className="status-wrapper">
              <span className="status-label"> Funding Rate :</span>
              <span
                className={`status-value ${getFundingRateClass(
                  tickerData.funding_rate !== null
                    ? parseFloat(tickerData.funding_rate)
                    : null
                )}`}
              >
                {tickerData.funding_rate !== null
                  ? formatNumber(
                      String(Number(tickerData.funding_rate) * 100),
                      4
                    )
                  : "--"}
                %
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }
);

TickerInfoBar.displayName = "TickerInfoBar";

export default TickerInfoBar;
