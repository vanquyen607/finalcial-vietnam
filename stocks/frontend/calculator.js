/* calculator.js — Tính phí giao dịch & Giá hòa vốn */
"use strict";
(function () {
  const $ = (s, r) => (r || document).querySelector(s);

  function fmt(n, d = 0) {
    if (n == null || isNaN(n)) return "—";
    return Number(n).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  function calculate() {
    const buyPrice = parseFloat($("#calcBuyPrice").value) || 0;
    const qty = parseFloat($("#calcQty").value) || 0;
    const feeBuyPct = parseFloat($("#calcFeeBuy").value) || 0.15;
    const feeSellPct = parseFloat($("#calcFeeSell").value) || 0.15;
    const taxPct = parseFloat($("#calcTax").value) || 0.1;
    const targetPrice = parseFloat($("#calcTargetPrice").value) || 0;

    if (!buyPrice || !qty) return;

    const totalCost = buyPrice * qty;
    const feeBuyVal = totalCost * (feeBuyPct / 100);
    const costBasis = totalCost + feeBuyVal;

    // Hòa vốn: Giá bán P_sell sao cho: P_sell * qty * (1 - (feeSellPct + taxPct)/100) = costBasis
    const sellDeduction = (feeSellPct + taxPct) / 100;
    const breakevenTotal = costBasis / (1 - sellDeduction);
    const breakevenPrice = breakevenTotal / qty;

    $("#calcResCost").textContent = fmt(costBasis);
    $("#calcResBEPrice").textContent = fmt(breakevenPrice, 1);
    $("#calcResBEPct").textContent = "+" + fmt(((breakevenPrice / buyPrice) - 1) * 100, 2) + "%";

    if (targetPrice > 0) {
      const revenue = targetPrice * qty;
      const sellFeeAndTax = revenue * sellDeduction;
      const netGain = revenue - sellFeeAndTax - costBasis;
      const netPct = (netGain / costBasis) * 100;

      const pEl = $("#calcResProfit");
      pEl.textContent = (netGain >= 0 ? "+" : "") + fmt(netGain) + ` (${netPct >= 0 ? "+" : ""}${fmt(netPct, 1)}%)`;
      pEl.className = "pp-v " + (netGain >= 0 ? "up" : "down");
    } else {
      $("#calcResProfit").textContent = "—";
      $("#calcResProfit").className = "pp-v";
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = $("#btnSideCalc");
    const panel = $("#calcPanel");
    const close = $("#btnCloseCalc");

    if (btn && panel) {
      btn.addEventListener("click", () => {
        panel.hidden = !panel.hidden;
      });
    }

    if (close && panel) {
      close.addEventListener("click", () => { panel.hidden = true; });
    }

    ["calcBuyPrice", "calcQty", "calcFeeBuy", "calcFeeSell", "calcTax", "calcTargetPrice"].forEach(id => {
      const el = $("#" + id);
      if (el) el.addEventListener("input", calculate);
    });
  });
})();

