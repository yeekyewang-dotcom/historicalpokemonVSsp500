# Pokémon Base Set vs S&P 500: a 5-year historical backtest (2021–2025)

A **static, one-time** companion to the live daily model. Academic simulation, not investment advice.

Unlike the live model, this one does not update itself and has no automation to set up:
it is a fixed snapshot built once from researcher-collected data (`calc.py` + the figures in it),
rendered by `docs/index.html`. There is nothing to run daily.

## How it works
`calc.py` holds every input (the 4 cards' USD annual averages, the S&P 500 USD annual averages,
the USD/GBP rates used, and all cost/tax/weight assumptions), computes the annual-frequency
backtest, and writes `docs/data.js`, a plain JS object the page reads directly — no server,
no fetch, no build step. `docs/index.html` is the whole site.

## Putting it online (same steps as the live model)
1. New GitHub repo, push this folder.
2. Settings → Pages → Deploy from branch → `main` / `/docs`.
3. Done — no Actions workflow needed, nothing to run. Give it a minute, then open
   `https://<your-username>.github.io/<repo-name>/`.

## If you ever want to change a number
Edit the relevant line in `calc.py`, re-run `python3 calc.py`, which rewrites `docs/data.js`,
then commit both files. The page always reflects whatever `calc.py` last computed.

## Known limitations (also stated on the site itself)
- 2024/2025 S&P 500 figures are averages of the months with a verified close (8/12 and 4/12
  respectively), not a full 12-month average like 2021–2023.
- Only 5 annual data points per asset — momentum/trend/volatility are small-sample estimates.
- Card prices are DERIVED (a researcher-calculated average), not single dated sales.
- No volume/liquidity data exists for past years, so that scoring factor was dropped here
  (see the site's Methodology section for the reweighting).
