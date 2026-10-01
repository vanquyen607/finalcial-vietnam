import { describe, expect, it } from "vitest";
import type { LiveTick } from "./useLiveSeries";
import { basePoints, mergeLive } from "./useLiveSeries";

describe("mergeLive", () => {
  it("live rỗng -> giữ nguyên base", () => {
    const base = [{ time: 1, value: 100 }];
    expect(mergeLive(base, [])).toBe(base);
  });

  it("base rỗng -> giữ nguyên ts (epoch giây)", () => {
    const live: LiveTick[] = [{ ts: 1_790_750_000, buy: 50 }];
    expect(mergeLive([], live)).toEqual([{ time: 1790750000, value: 50 }]);
  });

  it("daily (time chuỗi) -> cập nhật điểm cuối bằng tick mới nhất", () => {
    const base = [
      { time: "2026-09-28", value: 100 },
      { time: "2026-09-29", value: 101 },
    ];
    const live: LiveTick[] = [
      { ts: 1_000_000, buy: 102 },
      { ts: 1_000_060, buy: 103 },
    ];
    const out = mergeLive(base, live);
    expect(out).toHaveLength(2);
    expect(out[1]).toEqual({ time: "2026-09-29", value: 103 });
    expect(out[0]).toEqual({ time: "2026-09-28", value: 100 });
  });

  it("intraday -> khử trùng + sắp xếp theo thời gian", () => {
    const base = [
      { time: 300, value: 3 },
      { time: 100, value: 1 },
    ];
    const live: LiveTick[] = [
      { ts: 200, buy: 2 },
      { ts: 100, buy: 9 }, // trùng 100 -> ghi đè
    ];
    expect(mergeLive(base, live)).toEqual([
      { time: 100, value: 9 },
      { time: 200, value: 2 },
      { time: 300, value: 3 },
    ]);
  });
});

describe("basePoints", () => {
  const hist = {
    daily: [
      { date: "2026-09-28", buy: 100 },
      { date: "2026-09-29", buy: 101 },
      { date: "2026-09-30", buy: 102 },
    ],
    intraday: [{ ts: 1_790_750_000, buy: 103 }],
  };

  it("24h -> intraday giữ nguyên ts giây", () => {
    expect(basePoints(hist, "24h")).toEqual([{ time: 1790750000, value: 103 }]);
  });

  it("7d/30d -> daily cắt theo kỳ", () => {
    expect(basePoints(hist, "7d")).toHaveLength(3);
    expect(basePoints(hist, "30d")[0]).toEqual({ time: "2026-09-28", value: 100 });
  });

  it("mã mới chưa có daily -> fallback intraday cho mọi range", () => {
    const fresh = { daily: [], intraday: hist.intraday };
    expect(basePoints(fresh, "30d")).toEqual([{ time: 1790750000, value: 103 }]);
    expect(basePoints(fresh, "7d")).toEqual([{ time: 1790750000, value: 103 }]);
  });
});
