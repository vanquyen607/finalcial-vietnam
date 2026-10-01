import { describe, expect, it } from "vitest";
import { groupQuotes } from "./groupQuotes";
import type { BrandInfo, GoldType, Quote } from "./types";

function meta(code: string, brand: string, product: string, featured = false): GoldType {
  return {
    code,
    name: `${brand} ${product}`,
    brand,
    product,
    unit: "VND",
    per: "lượng",
    category: "other",
    featured,
    alias: code.toLowerCase(),
  };
}

function quote(code: string, buy: number, change = 0): Quote {
  return {
    ts: 1_790_750_000,
    code,
    name: code,
    buy,
    sell: buy + 1_000_000,
    change_buy: change,
    change_sell: change,
    unit: "VND",
    per: "lượng",
    source: "test",
  };
}

const META: Record<string, GoldType> = Object.fromEntries(
  [
    meta("XAUUSD", "Spot", "Spot", true),
    meta("SJL1L10", "SJC", "Miếng 9999", true),
    meta("SJ9999", "SJC", "Nhẫn trơn", true),
    meta("VNGSJC", "SJC", "Vàng SJC"),
    meta("NT_SJC", "Ngọc Thẩm", "SJC"),
    meta("NT_9999", "Ngọc Thẩm", "9999"),
    meta("UNKNOWN1", "brand-la", "Sản phẩm lạ"),
  ].map((t) => [t.code, t]),
);

const BRANDS: BrandInfo[] = [
  { brand: "Spot", label: "Vàng thế giới", order: 0, count: 1 },
  { brand: "SJC", label: "SJC", order: 1, count: 3 },
  { brand: "Ngọc Thẩm", label: "Ngọc Thẩm", order: 9, count: 2 },
];

const QUOTES: Quote[] = [
  quote("NT_SJC", 143_000_000, -500_000),
  quote("SJ9999", 141_000_000, 100_000),
  quote("VNGSJC", 139_000_000, 0),
  quote("UNKNOWN1", 0, 0), // giá 0 -> không tính vào khoảng giá
  quote("NT_9999", 138_000_000, -100_000),
  quote("XAUUSD", 4_180, 12),
  quote("SJL1L10", 143_500_000, 1_000_000),
];

describe("groupQuotes", () => {
  const groups = groupQuotes(QUOTES, META, BRANDS);

  it("sắp nhóm theo thứ tự brands: thế giới trước, thương hiệu lạ cuối", () => {
    expect(groups.map((g) => g.label)).toEqual([
      "Vàng thế giới",
      "SJC",
      "Ngọc Thẩm",
      "brand-la",
    ]);
    expect(groups[3].order).toBe(1000);
  });

  it("gộp đủ sản phẩm, trong nhóm: mã nổi bật trước rồi theo tên", () => {
    const sjc = groups.find((g) => g.brand === "SJC")!;
    expect(sjc.items.map((q) => q.code)).toEqual(["SJL1L10", "SJ9999", "VNGSJC"]);

    const nt = groups.find((g) => g.brand === "Ngọc Thẩm")!;
    expect(nt.items).toHaveLength(2);
    expect(groups.reduce((n, g) => n + g.items.length, 0)).toBe(QUOTES.length);
  });

  it("tính khoảng giá (bỏ giá ≤ 0) và số mã tăng/giảm đứng yên", () => {
    const sjc = groups.find((g) => g.brand === "SJC")!;
    expect(sjc.minBuy).toBe(139_000_000);
    expect(sjc.maxBuy).toBe(143_500_000);
    expect([sjc.up, sjc.down, sjc.flat]).toEqual([2, 0, 1]);

    const nt = groups.find((g) => g.brand === "Ngọc Thẩm")!;
    expect([nt.up, nt.down, nt.flat]).toEqual([0, 2, 0]);
    expect(nt.unit).toBe("VND");

    const la = groups.find((g) => g.brand === "brand-la")!;
    expect(la.minBuy).toBe(0); // không có giá hợp lệ
    expect(la.maxBuy).toBe(0);
  });

  it("brands rỗng -> giữ thứ tự symbol của backend (Spot trước, brand lạ cuối)", () => {
    const fallback = groupQuotes(QUOTES, META, []);
    expect(fallback[0].brand).toBe("Spot");
    expect(fallback[1].brand).toBe("SJC");
    expect(fallback.at(-1)!.brand).toBe("brand-la");
  });

  it("brands rỗng vẫn hiện nhãn (dùng nguyên khóa brand, không lỗi)", () => {
    const fallback = groupQuotes(QUOTES, META, []);
    expect(fallback[0].label).toBe("Spot");
    expect(fallback.find((g) => g.brand === "brand-la")!.label).toBe("brand-la");
  });
});
