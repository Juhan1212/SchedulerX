import { useState, useMemo } from "react";
import Icon from "../shared/SVGIcon";
import { createWebSocketStore } from "../../states/chartState";

const timeIntervals = [
  ["1m", "5m", "15m", "30m"],
  ["1h", "4h", "8h"],
  ["1d", "7d", "30d"],
];

export default function TimeSelector({
  store,
  onIntervalChange,
}: {
  store: ReturnType<typeof createWebSocketStore>;
  onIntervalChange?: (newInterval: string) => void;
}) {
  const { interval, setInterval } = store.getState();
  const [isOpen, setIsOpen] = useState(false);

  const handleIntervalChange = (time: string) => {
    setInterval(time);
    if (onIntervalChange) {
      onIntervalChange(time);
    }
  };

  const modalContent = useMemo(() => {
    if (!isOpen) return null;

    return (
      <>
        <div className="modal-header">
          <h4 className="modal-title">시간 간격</h4>
        </div>
        <div className="interval-grid">
          {timeIntervals.flat().map((time) => (
            <button
              key={time}
              onClick={() => {
                handleIntervalChange(time);
                setIsOpen(false);
              }}
              className={`interval-option ${interval === time ? "filled" : ""}`}
            >
              {time}
            </button>
          ))}
        </div>
      </>
    );
  }, [interval, isOpen]);

  return (
    <div className="time-interval-container">
      {/* Top Bar */}
      <div className="time-interval-bar">
        <Icon type="clock" className="time-interval-icon" />
        {["1m", "5m", "15m", "1h", "4h", "1d"].map((time) => (
          <button
            key={time}
            onClick={() => handleIntervalChange(time)}
            className={`interval-btn ${interval === time ? "active" : ""}`}
          >
            {time}
          </button>
        ))}
        {/* Dropdown Toggle */}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="interval-btn-dropdown"
        >
          <Icon
            type="downFilled"
            className={`arrow-icon ${isOpen ? "open" : ""}`}
          />
        </button>
        <div className={`interval-modal ${isOpen ? "visible" : ""}`}>
          {modalContent}
        </div>
      </div>
    </div>
  );
}
