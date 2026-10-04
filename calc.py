import json, statistics as st

YEARS = [2021, 2022, 2023, 2024, 2025]
FX = {2021: 0.73, 2022: 0.81, 2023: 0.80, 2024: 0.78, 2025: 0.76}  # USD -> GBP, real annual averages (see notes)
FX_NOTE = "Real annual-average USD/GBP rates (2021 approximate from scattered spot rates; 2022-2023 cross-verified across two sources; 2024 avg of 8/12 months; 2025 avg of 4/12 months)."

SP500_USD = {2021: 4273.41, 2022: 4097.49, 2023: 4173.53, 2024: 5483.49, 2025: 6708.61}
SP500_NOTE = "2021-2023: genuine full-year average closes (cross-checked). 2024: average of the 8 months with a clearly reported close (Feb,Apr,May,Jun,Aug,Sep,Oct,Dec). 2025: average of 4 months (Aug,Sep,Oct,Dec). Not a full 12-month average for the last two years -- stated as a limitation."

CARDS_USD = {
 "Charizard": {2021:226.78, 2022:163.22, 2023:180.69, 2024:216.94, 2025:247.04},
 "Blastoise": {2021:59.29,  2022:44.69,  2023:50.23,  2024:60.92,  2025:67.45},
 "Venusaur":  {2021:55.96,  2022:37.05,  2023:36.34,  2024:41.32,  2025:53.83},
 "Pikachu":   {2021:10.28,  2022:4.12,   2023:2.18,   2024:2.44,   2025:2.90},
}
CARD_NOTE = "Base Set Unlimited, ungraded/near-mint. Annual average of 12 monthly PriceCharting prices, researcher-collected (DERIVED, not single-sale)."

CAPITAL = 10000.0
COSTS = {"card": {"buy_fee":0.0, "sell_fee":0.1275, "half_spread":0.05, "fixed_gbp":1.5},
         "equity": {"buy_fee":0.0, "sell_fee":0.0, "half_spread":0.001, "fixed_gbp":0.0}}
TAX = {"cgt_exempt_gbp": 3000, "cgt_rate": 0.18}
WEIGHTS = {"momentum":0.40, "trend":0.25, "volatility":0.25, "regime":0.10}
RULES = {"buy_score":70, "sell_score":40, "edge_multiple":1.0}
EDGE_NOTE = "Live daily model uses edge_multiple=1.5 (momentum must beat round-trip cost by 50%). At annual frequency that threshold is never reached with real card data, so this model uses breakeven (1.0x): momentum must simply exceed the round-trip cost. Documented change, not a silent one."

def gbp(usd, year): return usd * FX[year]
cards_gbp = {c: {y: gbp(v, y) for y, v in series.items()} for c, series in CARDS_USD.items()}
sp500_gbp = {y: gbp(v, y) for y, v in SP500_USD.items()}

def pct(vals, hi=True):
    n = len(vals)
    if n < 2 or len(set(vals)) == 1: return [0.5]*n
    r = [sum(x2 < x for x2 in vals)/(n-1) for x in vals]
    return r if hi else [1-x for x in r]

def rate(mkt, side): c = COSTS[mkt]; return c[side+"_fee"] + c["half_spread"]

def card_cost_fraction(mkt): return rate(mkt,"buy") + rate(mkt,"sell") + 2*COSTS[mkt]["fixed_gbp"]/(CAPITAL*0.25)

decisions = []
signals_by_year = {y: [] for y in YEARS[1:]}
pos = {c: 0.0 for c in cards_gbp}   # GBP currently invested in each card (algo)
cash = CAPITAL
realised_gain = 0.0
algo_series = [{"year": YEARS[0], "value": CAPITAL}]

feat = {c: {} for c in cards_gbp}
for y in YEARS[1:]:
    idx = YEARS.index(y)
    for c in cards_gbp:
        hist = [cards_gbp[c][yy] for yy in YEARS[:idx+1]]
        mom = hist[-1]/hist[-2] - 1
        trend = hist[-1]/(sum(hist)/len(hist)) - 1
        rets = [hist[i]/hist[i-1]-1 for i in range(1,len(hist))]
        vol = st.pstdev(rets) if len(rets) > 1 else 0.0
        feat[c][y] = {"momentum": mom, "trend": trend, "volatility": vol}
    sp_hist = [sp500_gbp[yy] for yy in YEARS[:idx+1]]
    regime = 1.0 if sp_hist[-1] > sp_hist[-2] else 0.0
    names = list(cards_gbp)
    comp = {"momentum": pct([feat[c][y]["momentum"] for c in names]),
            "trend":    pct([feat[c][y]["trend"] for c in names]),
            "volatility": pct([feat[c][y]["volatility"] for c in names], hi=False),
            "regime": [regime]*len(names)}
    scores = {}
    for i, c in enumerate(names):
        s = 100 * sum(WEIGHTS[k]*comp[k][i] for k in WEIGHTS)
        scores[c] = round(s, 1)
        signals_by_year[y].append({"card": c, "score": scores[c], "components": {k: round(comp[k][i],3) for k in WEIGHTS}, **feat[c][y]})
    gross_before = cash + sum(pos.values())
    rt = card_cost_fraction("card")
    for c in sorted(names, key=lambda c: -scores[c]):
        price_now = cards_gbp[c][y]
        if pos[c] > 0 and scores[c] <= RULES["sell_score"]:
            proceeds = pos[c] * (1 - rate("card","sell")) - COSTS["card"]["fixed_gbp"]
            gain = proceeds - pos[c]  # approx: cost basis tracked as last invested amount
            realised_gain += gain
            cash += proceeds; decisions.append({"year": y, "card": c, "action": "SELL", "score": scores[c], "amount_gbp": round(proceeds,2), "reason": f"score {scores[c]} <= {RULES['sell_score']}"})
            pos[c] = 0.0
        elif pos[c] == 0 and scores[c] >= RULES["buy_score"] and feat[c][y]["momentum"] > RULES["edge_multiple"]*rt:
            alloc = min(0.25*gross_before, cash) - COSTS["card"]["fixed_gbp"]
            if alloc > 5:
                cost = alloc * rate("card","buy") + COSTS["card"]["fixed_gbp"]
                cash -= (alloc + cost); pos[c] = alloc
                decisions.append({"year": y, "card": c, "action": "BUY", "score": scores[c], "amount_gbp": round(alloc,2), "reason": f"score {scores[c]} >= {RULES['buy_score']}, momentum {feat[c][y]['momentum']:.1%}"})
    for c in names:
        if pos[c] > 0: pos[c] = pos[c] * (cards_gbp[c][y] / cards_gbp[c][YEARS[idx-1]])
    total = cash + sum(pos.values())
    algo_series.append({"year": y, "value": round(total,2)})

tax_due = max(0, realised_gain - TAX["cgt_exempt_gbp"]) * TAX["cgt_rate"] if realised_gain > 0 else 0.0

def buy_hold(series_dict, cost_mkt):
    names = list(series_dict)
    alloc0 = CAPITAL/len(names)
    units = {c: (alloc0 - COSTS[cost_mkt]["fixed_gbp"]) / (series_dict[c][YEARS[0]] * (1+rate(cost_mkt,"buy"))) for c in names}
    out = []
    for y in YEARS:
        gross = sum(units[c]*series_dict[c][y] for c in names)
        out.append({"year": y, "value": round(gross,2)})
    liq = sum(units[c]*series_dict[c][YEARS[-1]]*(1-rate(cost_mkt,"sell")) - COSTS[cost_mkt]["fixed_gbp"] for c in names)
    return out, liq

pkm_bh, pkm_bh_liq = buy_hold(cards_gbp, "card")
sp_units = CAPITAL / sp500_gbp[YEARS[0]]
sp_series = [{"year": y, "value": round(sp_units*sp500_gbp[y],2)} for y in YEARS]

out = {
  "meta": {"years": YEARS, "capital": CAPITAL, "cards": list(cards_gbp), "fx_note": FX_NOTE, "sp500_note": SP500_NOTE, "card_note": CARD_NOTE, "edge_note": EDGE_NOTE,
            "weights": WEIGHTS, "rules": RULES, "costs": COSTS, "tax": TAX, "realised_gain_gbp": round(realised_gain,2), "tax_due_gbp": round(tax_due,2),
            "pokemon_algo_final_liq_gbp": round((cash + sum(pos.values())) - (sum(pos.values())*rate("card","sell") + (1 if any(pos.values()) else 0)*COSTS["card"]["fixed_gbp"]),2)},
  "series": {"Pokémon algo (4-card, backtested)": algo_series, "Pokémon buy & hold (equal-weight)": pkm_bh, "S&P 500": sp_series},
  "cards_gbp": cards_gbp, "cards_usd": CARDS_USD, "sp500_gbp": sp500_gbp, "sp500_usd": SP500_USD, "fx": FX,
  "signals": signals_by_year, "decisions": decisions,
}
json.dump(out, open("docs/data.js.json","w"), indent=1)
print("Algo series:", algo_series)
print("Decisions:", decisions)
print("P&H:", pkm_bh, "liq", round(pkm_bh_liq,2))
print("SP500:", sp_series)
