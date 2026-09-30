/** Mã TradingView tương ứng cho từng code vàng nội bộ.
 *
 *  TradingView KHÔNG có giá vàng miếng SJC/DOJI/PNJ — chỉ có vàng thế giới,
 *  nên chỉ XAUUSD mới có tab TradingView.
 */
export interface TvTab {
  label: string;
  tv: string;
}

export const TV_TABS: Record<string, TvTab[]> = {
  XAUUSD: [
    { label: "Vàng thế giới", tv: "OANDA:XAUUSD" },
    { label: "PAX Gold 24/7", tv: "BINANCE:PAXGUSDT" },
  ],
};

export function tvTabsFor(code: string | undefined): TvTab[] | undefined {
  return code ? TV_TABS[code] : undefined;
}
