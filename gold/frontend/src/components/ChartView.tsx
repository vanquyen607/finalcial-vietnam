import { useEffect, useRef } from "react";
import { ColorType, createChart, CrosshairMode, LineStyle } from "lightweight-charts";
import type { IChartApi, ISeriesApi } from "lightweight-charts";

export interface ChartPoint {
  time: number | string;
  value: number;
}

interface Props {
  points: ChartPoint[];
  /** Vẽ thêm đường thứ hai (vd. giá bán) */
  secondary?: ChartPoint[];
  height?: number;
  positive?: boolean;
  /** Đơn vị giá để định dạng trục (VND → 140.500.000, USD → 4.183,00) */
  unit?: string;
  /** Đổi giá trị này (vd. đổi mã/khoảng thời gian) thì mới fit lại chart —
   *  để tick realtime không kéo reset zoom mỗi giây. */
  fitKey?: string;
}

const GOLD = "#d4af37";
const UP = "#30d158";
const DOWN = "#ff453a";

export default function ChartView({
  points,
  secondary,
  height = 300,
  positive = true,
  unit,
  fitKey,
}: Props) {
  const boxRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainRef = useRef<ISeriesApi<"Area"> | null>(null);
  const secRef = useRef<ISeriesApi<"Line"> | null>(null);
  // undefined → lần set data đầu tiên luôn fit toàn bộ dữ liệu
  const fitRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const priceFormat =
      unit === "USD"
        ? ({ type: "price", precision: 2, minMove: 0.01 } as const)
        : ({ type: "price", precision: 0, minMove: 1000 } as const);
    const chart = createChart(el, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#99907c",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1c1c1e" },
        horzLines: { color: "#1c1c1e" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#4d4635", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#2c2c2e" },
        horzLine: { color: "#4d4635", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#2c2c2e" },
      },
      rightPriceScale: { borderColor: "#2c2c2e" },
      timeScale: { borderColor: "#2c2c2e", timeVisible: true, secondsVisible: false },
      handleScroll: false,
      handleScale: false,
    });
    chartRef.current = chart;

    mainRef.current = chart.addAreaSeries({
      priceFormat,
      lineColor: positive ? UP : DOWN,
      topColor: positive ? "rgba(48,209,88,0.28)" : "rgba(255,69,58,0.28)",
      bottomColor: "rgba(48,209,88,0)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerBorderColor: GOLD,
      crosshairMarkerBackgroundColor: GOLD,
    });
    if (secondary) {
      secRef.current = chart.addLineSeries({
        priceFormat,
        color: GOLD,
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
    }

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }));
    ro.observe(el);
    // chart mới → lần set data kế tiếp phải fit lại
    fitRef.current = undefined;
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      mainRef.current = null;
      secRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height, Boolean(secondary), unit, positive]);

  useEffect(() => {
    if (!mainRef.current) return;
    // time đã là GIÂY (số) hoặc "YYYY-MM-DD" — không quy đổi thêm ở đây
    const data = points.map((p) => ({ time: p.time as never, value: p.value }));
    if (data.length) {
      mainRef.current.setData(data);
      const shouldFit = fitRef.current !== fitKey;
      fitRef.current = fitKey;
      if (shouldFit) chartRef.current?.timeScale().fitContent();
    }
    if (secRef.current && secondary) {
      secRef.current.setData(secondary.map((p) => ({ time: p.time as never, value: p.value })));
    }
  }, [points, secondary, fitKey]);

  return <div ref={boxRef} className="chart-box" style={{ height }} />;
}
