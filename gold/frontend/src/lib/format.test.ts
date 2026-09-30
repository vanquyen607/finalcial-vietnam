import { describe, expect, it } from "vitest";
import {
  changePct,
  fmtAgo,
  fmtCompact,
  fmtPct,
  fmtPrice,
  fmtSigned,
  tone,
} from "./format";

describe("fmtPrice", () => {
  it("VND đầy đủ", () => {
    expect(fmtPrice(140_500_000, "VND")).toBe("140.500.000");
    expect(fmtPrice(0, "VND")).toBe("0");
  });
  it("USD 2 thập phân", () => {
    expect(fmtPrice(4177.8, "USD")).toBe("4.177,80");
  });
  it("NaN/Infinity -> gạch ngang", () => {
    expect(fmtPrice(NaN, "VND")).toBe("—");
    expect(fmtPrice(Infinity, "USD")).toBe("—");
  });
});

describe("fmtCompact", () => {
  it("triệu rút gọn", () => {
    expect(fmtCompact(140_500_000, "VND")).toBe("140.5 tr");
    expect(fmtCompact(8_100_000, "VND")).toBe("8.10 tr");
  });
});

describe("fmtSigned", () => {
  it("dấu +/−/không", () => {
    expect(fmtSigned(1_000_000, "VND")).toBe("+1.00 tr");
    expect(fmtSigned(-500, "VND")).toBe("−500");
    expect(fmtSigned(0, "VND")).toBe("0");
    expect(fmtSigned(14.73, "USD")).toBe("+14,73");
  });
});

describe("changePct & fmtPct & tone", () => {
  it("tính % so với đầu ngày", () => {
    expect(changePct(102, 2)).toBe(2);
    expect(changePct(100, 0)).toBe(0);
    expect(changePct(0, 0)).toBe(0);
  });
  it("format %", () => {
    expect(fmtPct(1.5)).toBe("+1.50%");
    expect(fmtPct(-2)).toBe("−2.00%");
    expect(fmtPct(0)).toBe("0.00%");
  });
  it("tone", () => {
    expect(tone(1)).toBe("up");
    expect(tone(-1)).toBe("down");
    expect(tone(0)).toBe("flat");
  });
});

describe("fmtAgo", () => {
  it("giây/phút/giờ", () => {
    expect(fmtAgo(5)).toBe("5 giây trước");
    expect(fmtAgo(150)).toBe("2 phút trước");
    expect(fmtAgo(7200)).toBe("2 giờ trước");
  });
  it("âm/vô hạn -> vừa xong", () => {
    expect(fmtAgo(-1)).toBe("vừa xong");
  });
});
