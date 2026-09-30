import { describe, expect, it } from "vitest";
import type { LiveTick } from "./useLiveSeries";
import { mergeLive } from "./useLiveSeries";

describe("mergeLive", () => {
  it("live rỗng -> giữ nguyên base", () => {
    const base = [{ time: 1, value: 100 }];
    expect(mergeLive(base, [])).toBe(base);
  });

  it("base rỗng -> đổi tick sang giây", () => {
    const live: LiveTick[] = [{ ts: 1_790_750_000_000, buy: 50 }];
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
      { ts: 200_000, buy: 2 }, // -> 200
      { ts: 100_000, buy: 9 }, // trùng 100 -> ghi đè
    ];
    expect(mergeLive(base, live)).toEqual([
      { time: 100, value: 9 },
      { time: 200, value: 2 },
      { time: 300, value: 3 },
    ]);
  });
});
