import { createWebSocketStore } from "../src/states/chartState";

describe("Upbit WebSocket", () => {
  it("should receive candlestick or ticker data from Upbit", async () => {
    await new Promise((resolve, reject) => {
      const wsStore = createWebSocketStore({
        exchange: "UPBIT",
        symbol: "BTC",
        interval: "1m",
      });

      let received = false;
      const timeout = setTimeout(() => {
        if (!received) {
          reject(new Error("No data received from Upbit WebSocket within 10s"));
        }
      }, 10000);

      wsStore.getState().connectWebSocket();
      wsStore.getState().addMessageListener((data) => {
        console.log("Received data from Upbit WebSocket:", data);
        if (!received) {
          received = true;
          clearTimeout(timeout);
          wsStore.getState().disconnectWebSocket();
          expect(data).toBeDefined();
          resolve(data);
        }
      });
    });
  });
});

test("getTime", () => {
  const now = new Date("2025-07-10T14:15:29" + "Z").getTime(); // "Z"를 붙이면 UTC로 인식
  console.log(now);
  expect(now).toBe(1752466529000);
});

test("tofixed", () => {
  const value = 123456789.125456789;
  const fixedValue = value.toFixed(2);
  console.log(fixedValue); // "123456789.12"
  expect(fixedValue).toBe("123456789.12");
});
