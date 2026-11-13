import { useEffect, useRef } from "react";
import { ColorType, createChart, CrosshairMode, LineStyle } from "lightweight-charts";
import type { AutoscaleInfo, IChartApi, ISeriesApi } from "lightweight-charts";
import { useTheme } from "../lib/useTheme";

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

const GOLD = "#c08a1e";
const INK_LIGHT = "#1a1f28";
const PAPER_DARK = "#e8ecf2";

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
  const mainRef = useRef<ISeriesApi<"Line"> | null>(null);
  const secRef = useRef<ISeriesApi<"Line"> | null>(null);
  const { theme } = useTheme();
  const isLight = theme === "light";
  // undefined → lần set data đầu tiên luôn fit toàn bộ dữ liệu
  const fitRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const priceFormat =
      unit === "USD"
        ? ({ type: "price", precision: 2, minMove: 0.01 } as const)
        : ({ type: "price", precision: 0, minMove: 1000 } as const);
    // Nhãn trục giá gọn: 140.500.000 -> "140,5 tr", 4.183,2 -> "4.183,20".
    const priceFormatter = (p: number) =>
      unit === "USD"
        ? p.toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : `${(p / 1_000_000).toFixed(1).replace(".", ",")} tr`;
    // Giá vàng đứng yên vài giờ khiến trục co về ±vài nghìn đồng; ép tối thiểu
    // để biểu đồ không "phóng to nhiễu" và không thành một khối màu.
    const minRange = unit === "USD" ? 2 : 400_000;
    const autoscaleInfoProvider = (original: () => AutoscaleInfo | null): AutoscaleInfo | null => {
      const res = original();
      const range = res?.priceRange;
      if (!range) return res;
      if (range.maxValue - range.minValue >= minRange) return res;
      const mid = (range.maxValue + range.minValue) / 2;
      return {
        ...res,
        priceRange: { minValue: mid - minRange / 2, maxValue: mid + minRange / 2 },
      };
    };
    const chart = createChart(el, {
      height,
      localization: { priceFormatter },
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: isLight ? "#3d4552" : "#b9c0cc",
        fontFamily: "'Chivo Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: isLight ? "#d8dde4" : "#262d38" },
        horzLines: { color: isLight ? "#d8dde4" : "#262d38" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: isLight ? "#9aa3b0" : "#4a5361", width: 1, style: LineStyle.Dashed, labelBackgroundColor: isLight ? "#f6f7f9" : "#1c222c" },
        horzLine: { color: isLight ? "#9aa3b0" : "#4a5361", width: 1, style: LineStyle.Dashed, labelBackgroundColor: isLight ? "#f6f7f9" : "#1c222c" },
      },
      rightPriceScale: { borderColor: isLight ? "#d8dde4" : "#2c3440" },
      timeScale: { borderColor: isLight ? "#d8dde4" : "#2c3440", timeVisible: true, secondsVisible: false },
      handleScroll: false,
      handleScale: false,
    });
    chartRef.current = chart;

    mainRef.current = chart.addLineSeries({
      priceFormat,
      color: isLight ? INK_LIGHT : PAPER_DARK,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      crosshairMarkerBorderColor: GOLD,
      crosshairMarkerBackgroundColor: GOLD,
      autoscaleInfoProvider,
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

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth });
      // Đổi bề rộng (xoay máy/zoom) phải fit lại, nếu không chỉ thấy vài ngày cuối.
      chart.timeScale().fitContent();
    });
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
    if (!chartRef.current) return;
    const isLight = theme === "light";
    chartRef.current.applyOptions({
      layout: { textColor: isLight ? "#3d4552" : "#b9c0cc" },
      grid: {
        vertLines: { color: isLight ? "#d8dde4" : "#262d38" },
        horzLines: { color: isLight ? "#d8dde4" : "#262d38" },
      },
      crosshair: {
        vertLine: { color: isLight ? "#9aa3b0" : "#4a5361", labelBackgroundColor: isLight ? "#f6f7f9" : "#1c222c" },
        horzLine: { color: isLight ? "#9aa3b0" : "#4a5361", labelBackgroundColor: isLight ? "#f6f7f9" : "#1c222c" },
      },
      rightPriceScale: { borderColor: isLight ? "#d8dde4" : "#2c3440" },
      timeScale: { borderColor: isLight ? "#d8dde4" : "#2c3440" },
    });
    mainRef.current?.applyOptions({ color: isLight ? INK_LIGHT : PAPER_DARK });
  }, [theme]);

  useEffect(() => {
    if (!mainRef.current) return;
    // lightweight-charts hiển thị mốc giờ theo UTC; cộng bù offset để trục giờ
    // khớp giờ Việt Nam (UTC+7) thay vì lệch 7 tiếng.
    const tzShift = -new Date().getTimezoneOffset() * 60;
    const toTime = (t: number | string) => (typeof t === "number" ? t + tzShift : t);
    const data = points.map((p) => ({ time: toTime(p.time) as never, value: p.value }));
    if (data.length) {
      mainRef.current.setData(data);
      const shouldFit = fitRef.current !== fitKey;
      fitRef.current = fitKey;
      if (shouldFit) chartRef.current?.timeScale().fitContent();
    }
    if (secRef.current && secondary) {
      secRef.current.setData(secondary.map((p) => ({ time: toTime(p.time) as never, value: p.value })));
    }
  }, [points, secondary, fitKey]);

  return <div ref={boxRef} className="chart-box" style={{ height }} />;
}
