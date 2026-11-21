export interface GoldType {
  code: string;
  name: string;
  brand: string;
  product: string;
  unit: "VND" | "USD";
  per: string;
  category: string;
  featured: boolean;
  alias: string;
}

export interface BrandInfo {
  brand: string;
  label: string;
  order: number;
}

export interface BrandGroup {
  brand: string;
  label: string;
  order: number;
  count: number;
  items: GoldType[];
}

export const BRANDS: BrandInfo[] = [
  { brand: "Spot", label: "Vàng thế giới", order: 0 },
  { brand: "SJC", label: "SJC", order: 1 },
  { brand: "DOJI", label: "DOJI", order: 2 },
  { brand: "PNJ", label: "PNJ", order: 3 },
  { brand: "BTMC", label: "Bảo Tín Minh Châu", order: 4 },
  { brand: "VietinBank", label: "VietinBank", order: 5 },
  { brand: "Mi Hồng", label: "Mi Hồng", order: 6 },
  { brand: "Phú Quý", label: "Phú Quý", order: 7 },
  { brand: "BTMH", label: "Bảo Tín Mạnh Hải", order: 8 },
  { brand: "Ngọc Thẩm", label: "Ngọc Thẩm", order: 9 },
  { brand: "Huy Thanh", label: "Huy Thanh Jewelry", order: 20 },
  { brand: "Kim Tín", label: "Kim Tín", order: 21 },
  { brand: "Kim Thành H", label: "Kim Thành H", order: 22 },
  { brand: "Kim Ngân Phúc", label: "Kim Ngân Phúc", order: 23 },
];

export const BRAND_BY_KEY: Record<string, BrandInfo> = Object.fromEntries(
  BRANDS.map((b) => [b.brand, b]),
);

export const DEFAULT_ORDER = 1000;

export function brandOrder(brand: string): number {
  return BRAND_BY_KEY[brand]?.order ?? DEFAULT_ORDER;
}

export function brandLabel(brand: string): string {
  return BRAND_BY_KEY[brand]?.label ?? brand;
}

export const GOLD_TYPES: GoldType[] = [
  { code: "SJL1L10", name: "SJC 9999", brand: "SJC", product: "Miếng 9999", unit: "VND", per: "lượng", category: "sjc", featured: true, alias: "sjc" },
  { code: "SJ9999", name: "SJC nhẫn trơn", brand: "SJC", product: "Nhẫn trơn", unit: "VND", per: "lượng", category: "sjc", featured: true, alias: "sjc-ring" },
  { code: "VNGSJC", name: "Vàng SJC", brand: "SJC", product: "Vàng SJC", unit: "VND", per: "lượng", category: "sjc", featured: false, alias: "vn-gold-sjc" },
  { code: "DOHNL", name: "DOJI Hà Nội", brand: "DOJI", product: "Hà Nội", unit: "VND", per: "lượng", category: "doji", featured: true, alias: "doji-hn" },
  { code: "DOHCML", name: "DOJI TP.HCM", brand: "DOJI", product: "TP.HCM", unit: "VND", per: "lượng", category: "doji", featured: true, alias: "doji-hcm" },
  { code: "DOJINHTV", name: "DOJI trang sức", brand: "DOJI", product: "Trang sức", unit: "VND", per: "lượng", category: "doji", featured: false, alias: "doji-jewelry" },
  { code: "PQHNVM", name: "PNJ Hà Nội", brand: "PNJ", product: "Hà Nội", unit: "VND", per: "lượng", category: "pnj", featured: true, alias: "pnj-hn" },
  { code: "PQHN24NTT", name: "PNJ 24K", brand: "PNJ", product: "24K", unit: "VND", per: "lượng", category: "pnj", featured: true, alias: "pnj-24k" },
  { code: "BTSJC", name: "Bảo Tín Minh Châu SJC", brand: "BTMC", product: "SJC", unit: "VND", per: "lượng", category: "btmc", featured: false, alias: "btmc-sjc" },
  { code: "BT9999NTT", name: "Bảo Tín Minh Châu 9999", brand: "BTMC", product: "9999", unit: "VND", per: "lượng", category: "btmc", featured: false, alias: "btmc-9999" },
  { code: "VIETTINMSJC", name: "VietinBank SJC", brand: "VietinBank", product: "SJC", unit: "VND", per: "lượng", category: "other", featured: false, alias: "viettin-sjc" },
  { code: "XAUUSD", name: "Giá vàng thế giới", brand: "Spot", product: "Spot", unit: "USD", per: "ounce", category: "world", featured: true, alias: "xauusd" },
  { code: "MH_SJC", name: "Mi Hồng SJC", brand: "Mi Hồng", product: "SJC", unit: "VND", per: "lượng", category: "mh", featured: false, alias: "mh-sjc" },
  { code: "MH_9999", name: "Mi Hồng 999", "brand": "Mi Hồng", product: "999", unit: "VND", per: "lượng", category: "mh", featured: false, alias: "mh-9999" },
  { code: "BTMH_9999", name: "Bảo Tín Mạnh Hải 9999", brand: "BTMH", product: "9999", unit: "VND", per: "lượng", category: "btmh", featured: false, alias: "btmh-9999" },
  { code: "PQ_SJC", name: "Phú Quý SJC", brand: "Phú Quý", product: "SJC", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-sjc" },
  { code: "PQ_9999", name: "Phú Quý 9999", brand: "Phú Quý", product: "9999", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-9999" },
  { code: "NT_9999", name: "Ngọc Thẩm 9999", brand: "Ngọc Thẩm", product: "9999", unit: "VND", per: "lượng", category: "nt", featured: false, alias: "nt-9999" },
  { code: "NT_SJC", name: "Ngọc Thẩm SJC", brand: "Ngọc Thẩm", product: "SJC", unit: "VND", per: "lượng", category: "nt", featured: false, alias: "nt-sjc" },
  { code: "SJC_1CHI", name: "SJC 1 chỉ", brand: "SJC", product: "1 chỉ", unit: "VND", per: "lượng", category: "sjc", featured: false, alias: "sjc-1-chi" },
  { code: "SJC_5CHI", name: "SJC 5 chỉ", brand: "SJC", product: "5 chỉ", unit: "VND", per: "lượng", category: "sjc", featured: false, alias: "sjc-5-chi" },
  { code: "SJC_NHAN_05", name: "SJC nhẫn 99,99 0,5 chỉ", brand: "SJC", product: "Nhẫn 0,5 chỉ", unit: "VND", per: "lượng", category: "sjc", featured: false, alias: "sjc-ring-05" },
  { code: "SJC_NHAN_1", name: "SJC nhẫn 99,99 1 chỉ", brand: "SJC", product: "Nhẫn 1 chỉ", unit: "VND", per: "lượng", category: "sjc", featured: false, alias: "sjc-ring-1" },
  { code: "DOJI_SJC_DN", name: "DOJI SJC Đà Nẵng", brand: "DOJI", product: "SJC Đà Nẵng", unit: "VND", per: "lượng", category: "doji", featured: false, alias: "doji-sjc-dn" },
  { code: "DOJI_RING", name: "DOJI nhẫn 9999 HTV", brand: "DOJI", product: "Nhẫn HTV", unit: "VND", per: "lượng", category: "doji", featured: false, alias: "doji-ring" },
  { code: "DOJI_24K", name: "DOJI 24K", brand: "DOJI", product: "24K", unit: "VND", per: "lượng", category: "doji", featured: false, alias: "doji-24k" },
  { code: "DOJI_PL_HN", name: "DOJI Phúc Long Hà Nội", brand: "DOJI", product: "Phúc Long HN", unit: "VND", per: "lượng", category: "doji", featured: false, alias: "doji-pl-hn" },
  { code: "DOJI_PL_HCM", name: "DOJI Phúc Long TP.HCM", brand: "DOJI", product: "Phúc Long HCM", unit: "VND", per: "lượng", category: "doji", featured: false, alias: "doji-pl-hcm" },
  { code: "DOJI_PL_DN", name: "DOJI Phúc Long Đà Nẵng", brand: "DOJI", product: "Phúc Long ĐN", unit: "VND", per: "lượng", category: "doji", featured: false, alias: "doji-pl-dn" },
  { code: "PNJ_KIMBAO", name: "PNJ Kim Bảo 9999", brand: "PNJ", product: "Kim Bảo", unit: "VND", per: "lượng", category: "pnj", featured: false, alias: "pnj-kim-bao" },
  { code: "PNJ_PHUCLOC", name: "PNJ Phúc Lộc Tài 9999", brand: "PNJ", product: "Phúc Lộc Tài", unit: "VND", per: "lượng", category: "pnj", featured: false, alias: "pnj-phuc-loc" },
  { code: "PNJ_PHOENIX", name: "PNJ Phượng Hoàng", brand: "PNJ", product: "Phượng Hoàng", unit: "VND", per: "lượng", category: "pnj", featured: false, alias: "pnj-phuong-hoang" },
  { code: "BTMC_RTL", name: "BTMC Rồng Thăng Long", brand: "BTMC", product: "Rồng Thăng Long", unit: "VND", per: "lượng", category: "btmc", featured: false, alias: "btmc-rtl" },
  { code: "BTMC_TS9999", name: "BTMC trang sức 9999", brand: "BTMC", product: "Trang sức 9999", unit: "VND", per: "lượng", category: "btmc", featured: false, alias: "btmc-ts-9999" },
  { code: "BTMC_TS999", name: "BTMC trang sức 999", brand: "BTMC", product: "Trang sức 999", unit: "VND", per: "lượng", category: "btmc", featured: false, alias: "btmc-ts-999" },
  { code: "MH_985", name: "Mi Hồng 985", brand: "Mi Hồng", product: "985", unit: "VND", per: "lượng", category: "mh", featured: false, alias: "mh-985" },
  { code: "MH_980", name: "Mi Hồng 980", brand: "Mi Hồng", product: "980", unit: "VND", per: "lượng", category: "mh", featured: false, alias: "mh-980" },
  { code: "MH_750", name: "Mi Hồng 750", brand: "Mi Hồng", product: "750", unit: "VND", per: "lượng", category: "mh", featured: false, alias: "mh-750" },
  { code: "MH_680", name: "Mi Hồng 680", brand: "Mi Hồng", product: "680", unit: "VND", per: "lượng", category: "mh", featured: false, alias: "mh-680" },
  { code: "MH_610", name: "Mi Hồng 610", brand: "Mi Hồng", product: "610", unit: "VND", per: "lượng", category: "mh", featured: false, alias: "mh-610" },
  { code: "PQ_999", name: "Phú Quý 999", brand: "Phú Quý", product: "999", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-999" },
  { code: "PQ_9999_BAR", name: "Phú Quý 9999 1 lượng", brand: "Phú Quý", product: "9999 1 lượng", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-9999-bar" },
  { code: "PQ_TS9999", name: "Phú Quý trang sức 9999", brand: "Phú Quý", product: "Trang sức 9999", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-ts-9999" },
  { code: "PQ_TS999", name: "Phú Quý trang sức 999", brand: "Phú Quý", product: "Trang sức 999", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-ts-999" },
  { code: "PQ_TS99", name: "Phú Quý trang sức 99", brand: "Phú Quý", product: "Trang sức 99", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-ts-99" },
  { code: "PQ_TS98", name: "Phú Quý trang sức 98", brand: "Phú Quý", product: "Trang sức 98", unit: "VND", per: "lượng", category: "pq", featured: false, alias: "pq-ts-98" },
  { code: "BTMH_999", name: "BTMH nữ trang 999", brand: "BTMH", product: "Nữ trang 999", unit: "VND", per: "lượng", category: "btmh", featured: false, alias: "btmh-999" },
  { code: "BTMH_RING", name: "BTMH nhẫn Kim Gia Bảo", brand: "BTMH", product: "Nhẫn Kim Gia Bảo", unit: "VND", per: "lượng", category: "btmh", featured: false, alias: "btmh-ring" },
  { code: "BTMH_DONG", name: "BTMH đồng vàng Kim Gia Bảo", brand: "BTMH", product: "Đồng vàng", unit: "VND", per: "lượng", category: "btmh", featured: false, alias: "btmh-dong" },
  { code: "NT_TA", name: "Ngọc Thẩm vàng ta", brand: "Ngọc Thẩm", product: "Vàng ta", unit: "VND", per: "lượng", category: "nt", featured: false, alias: "nt-vang-ta" },
  { code: "NT_18K", name: "Ngọc Thẩm 18K", brand: "Ngọc Thẩm", product: "18K", unit: "VND", per: "lượng", category: "nt", featured: false, alias: "nt-18k" },
  { code: "NT_TS750", name: "Ngọc Thẩm trang sức 750", brand: "Ngọc Thẩm", product: "Trang sức 750", unit: "VND", per: "lượng", category: "nt", featured: false, alias: "nt-ts-750" },
  { code: "HT_24K", name: "Huy Thanh 24K", brand: "Huy Thanh", product: "Vàng Huy Thanh 24K", unit: "VND", per: "lượng", category: "other", featured: false, alias: "huy-thanh-24k" },
  { code: "HT_22K", name: "Huy Thanh 22K", brand: "Huy Thanh", product: "Nguyên liệu 22K", unit: "VND", per: "lượng", category: "other", featured: false, alias: "huy-thanh-22k" },
  { code: "HT_18K", name: "Huy Thanh 18K", brand: "Huy Thanh", product: "Nguyên liệu 18K", unit: "VND", per: "lượng", category: "other", featured: false, alias: "huy-thanh-18k" },
  { code: "HT_14K", name: "Huy Thanh 14K", brand: "Huy Thanh", product: "Nguyên liệu 14K", unit: "VND", per: "lượng", category: "other", featured: false, alias: "huy-thanh-14k" },
  { code: "HT_10K", name: "Huy Thanh 10K", brand: "Huy Thanh", product: "Nguyên liệu 10K", unit: "VND", per: "lượng", category: "other", featured: false, alias: "huy-thanh-10k" },
  { code: "HT_MARKET", name: "Huy Thanh vàng thị trường 24K", brand: "Huy Thanh", product: "Vàng thị trường 24K", unit: "VND", per: "lượng", category: "other", featured: false, alias: "huy-thanh-thi-truong" },
  { code: "KT_RING9999", name: "Kim Tín nhẫn tròn 999.9", brand: "Kim Tín", product: "Nhẫn tròn 999.9", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-tin-nhan" },
  { code: "KT_SJC", name: "Kim Tín vàng miếng SJC", brand: "Kim Tín", product: "Vàng miếng SJC", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-tin-sjc" },
  { code: "KT_TS9999", name: "Kim Tín trang sức 999.9", brand: "Kim Tín", product: "Trang sức 999.9", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-tin-ts-9999" },
  { code: "KT_TS999", name: "Kim Tín trang sức 99.9", brand: "Kim Tín", product: "Trang sức 99.9", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-tin-ts-999" },
  { code: "KT_TS23K", name: "Kim Tín trang sức 99.7 (23K)", brand: "Kim Tín", product: "Trang sức 99.7 (23K)", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-tin-ts-23k" },
  { code: "KTH_RING9999", name: "Kim Thành H nhẫn trơn 99.99", brand: "Kim Thành H", product: "Nhẫn trơn 99.99", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-thanh-nhan" },
  { code: "KTH_RING990", name: "Kim Thành H nhẫn trơn 990", brand: "Kim Thành H", product: "Nhẫn trơn 990", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-thanh-990" },
  { code: "KTH_TS980", name: "Kim Thành H nữ trang 980", brand: "Kim Thành H", product: "Nữ trang 980", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-thanh-980" },
  { code: "KTH_TS610", name: "Kim Thành H nữ trang 610", brand: "Kim Thành H", product: "Nữ trang 610", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-thanh-610" },
  { code: "KTH_TS750", name: "Kim Thành H trang sức trắng 750", brand: "Kim Thành H", product: "Trang sức trắng 750", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-thanh-750" },
  { code: "KTH_TS416", name: "Kim Thành H trang sức 10K (416)", brand: "Kim Thành H", product: "Trang sức 10K (416)", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-thanh-416" },
  { code: "KNP_RING9999", name: "Kim Ngân Phúc nhẫn ép vỉ 9999", brand: "Kim Ngân Phúc", product: "Nhẫn ép vỉ 9999", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-ngan-phuc-nhan" },
  { code: "KNP_TS24K", name: "Kim Ngân Phúc trang sức 24K", brand: "Kim Ngân Phúc", product: "Trang sức 24K", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-ngan-phuc-ts-24k" },
  { code: "KP_RING9999", name: "Kim Phát nhẫn tròn 99.99", brand: "Kim Phát", product: "Nhẫn tròn 99.99", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-phat-nhan" },
  { code: "KP_TS985", name: "Kim Phát nữ trang 985", brand: "Kim Phát", product: "Nữ trang 985", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-phat-ts-985" },
  { code: "KP_TS750", name: "Kim Phát nữ trang 750", brand: "Kim Phát", product: "Nữ trang 750", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-phat-ts-750" },
  { code: "KP_TS610", name: "Kim Phát nữ trang 610", brand: "Kim Phát", product: "Nữ trang 610", unit: "VND", per: "lượng", category: "other", featured: false, alias: "kim-phat-ts-610" },
];

export const BY_CODE: Record<string, GoldType> = Object.fromEntries(
  GOLD_TYPES.map((t) => [t.code, t]),
);

export const BY_ALIAS: Record<string, GoldType> = Object.fromEntries(
  GOLD_TYPES.map((t) => [t.alias, t]),
);

export function featuredTypes(): GoldType[] {
  return GOLD_TYPES.filter((t) => t.featured);
}

export function brandGroups(featured = false): BrandGroup[] {
  const types = featured ? featuredTypes() : GOLD_TYPES;
  const buckets = new Map<string, GoldType[]>();
  for (const t of types) {
    const arr = buckets.get(t.brand) ?? [];
    arr.push(t);
    buckets.set(t.brand, arr);
  }
  const groups: BrandGroup[] = [];
  for (const [brand, items] of buckets.entries()) {
    const info = BRAND_BY_KEY[brand];
    groups.push({
      brand,
      label: info?.label ?? brand,
      order: info?.order ?? DEFAULT_ORDER,
      count: items.length,
      items,
    });
  }
  groups.sort((a, b) => a.order - b.order || a.label.localeCompare(b.label, "vi"));
  return groups;
}

export function resolve(ref: string): GoldType | null {
  if (BY_CODE[ref]) return BY_CODE[ref];
  return BY_ALIAS[ref.toLowerCase()] ?? null;
}
