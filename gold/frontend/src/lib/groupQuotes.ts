import type { BrandInfo, GoldType, Quote } from "./types";

/** Một nhóm nhà bán + các sản phẩm của họ, đã tính sẵn thống kê cho header. */
export interface QuoteGroup {
  brand: string;
  label: string;
  order: number;
  items: Quote[];
  /** giá mua thấp nhất / cao nhất trong nhóm (bỏ qua giá ≤ 0) */
  minBuy: number;
  maxBuy: number;
  unit: string;
  up: number;
  down: number;
  flat: number;
}

/** brand lạ (chưa có trong BRANDS của backend) -> xếp cuối bảng. */
const LAST_ORDER = 1000;

/**
 * Gộp bảng giá theo nhà bán.
 * - thứ tự nhóm lấy từ `brands` (backend đã sắp); nếu chưa có thì theo thứ tự
 *   xuất hiện của symbol trong `metaByCode` (giống thứ tự GOLD_TYPES).
 * - trong nhóm: mã nổi bật trước, rồi tên sản phẩm theo thứ tự tiếng Việt.
 */
export function groupQuotes(
  quotes: Quote[],
  metaByCode: Record<string, GoldType>,
  brands: BrandInfo[] = [],
): QuoteGroup[] {
  const brandOrder = new Map<string, number>();
  const brandLabel = new Map<string, string>();

  if (brands.length) {
    // backend đã sắp thứ tự -> dùng đúng, brand lạ (chưa khai báo) xếp cuối
    for (const b of brands) {
      brandOrder.set(b.brand, b.order);
      brandLabel.set(b.brand, b.label);
    }
  } else {
    // chưa nhận được brands (API chậm) -> giữ thứ tự symbol của backend
    let next = 0;
    for (const t of Object.values(metaByCode)) {
      if (!brandOrder.has(t.brand)) brandOrder.set(t.brand, next++);
      if (!brandLabel.has(t.brand)) brandLabel.set(t.brand, t.brand);
    }
  }

  const buckets = new Map<string, Quote[]>();
  for (const q of quotes) {
    const brand = metaByCode[q.code]?.brand ?? "";
    const list = buckets.get(brand);
    if (list) list.push(q);
    else buckets.set(brand, [q]);
  }

  const groups: QuoteGroup[] = [];
  for (const [brand, items] of buckets) {
    items.sort((a, b) => {
      const fa = metaByCode[a.code]?.featured ? 0 : 1;
      const fb = metaByCode[b.code]?.featured ? 0 : 1;
      if (fa !== fb) return fa - fb;
      const na = metaByCode[a.code]?.product || a.name;
      const nb = metaByCode[b.code]?.product || b.name;
      return na.localeCompare(nb, "vi");
    });

    let minBuy = Infinity;
    let maxBuy = -Infinity;
    let up = 0;
    let down = 0;
    let flat = 0;
    for (const q of items) {
      if (q.buy > 0) {
        minBuy = Math.min(minBuy, q.buy);
        maxBuy = Math.max(maxBuy, q.buy);
      }
      if (q.change_buy > 0) up += 1;
      else if (q.change_buy < 0) down += 1;
      else flat += 1;
    }

    groups.push({
      brand,
      label: brandLabel.get(brand) || brand,
      order: brandOrder.get(brand) ?? LAST_ORDER,
      items,
      minBuy: Number.isFinite(minBuy) ? minBuy : 0,
      maxBuy: Number.isFinite(maxBuy) ? maxBuy : 0,
      unit: items[0]?.unit ?? "VND",
      up,
      down,
      flat,
    });
  }

  groups.sort((a, b) => a.order - b.order || a.label.localeCompare(b.label, "vi"));
  return groups;
}
