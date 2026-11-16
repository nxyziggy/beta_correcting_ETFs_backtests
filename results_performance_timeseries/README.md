# Performance over time

Index-level time series for every main-case scoring portfolio, the equal-weight control and the ETF benchmark.

**Method.** Each portfolio is an index set to 100 at its window's start date, before the first trade, that then follows the back-tested portfolio value after modeled trading costs, in the convention of an index fact sheet's historical-performance chart. Levels are month-end values plus the final 2 November 2026 close; the first level is after initial deployment costs. US levels are in dollars and European levels in euros. All levels are hypothetical, back-tested results.

**Windows.**

| Region | Long window | Article window |
| --- | --- | --- |
| US | 30 June 2019 to 2 November 2026 | 30 September 2022 to 2 November 2026 |
| Europe | 30 June 2019 to 2 November 2026 | 30 September 2021 to 2 November 2026 |

Article windows restart the same rules on the article's start dates; they are not slices of the long-window paths.

**Portfolios.** The main case of the [scoring experiments](../results_recovery_experiments/REPORT.md): direct public-support screen, source timing, single-review exits, 10bp (US) and 15bp (Europe) trading costs.

| Series | Portfolio |
| --- | --- |
| `baseline_q50`, `baseline_q75` | Existing score, Q50 and Q75 entry rules |
| `trend_q50`, `trend_q75` | Baseline with fundamental improvement |
| `momentum_q50`, `momentum_q75` | Baseline with price momentum |
| `equal_weight` | Equal weights of every eligible, covered company |
| `etf_benchmark` | 60% SOXX / 40% ICLN (US); 50% EXV3.DE / 50% IQQH.DE (Europe), rebalanced monthly |

**Files.**

- [performance_timeseries.csv](performance_timeseries.csv): `region`, `window`, `window_start`, `series`, `date`, `index_level`; 32 series, 2,352 rows.
- [article_windows.csv](article_windows.csv): total return, CAGR, monthly maximum drawdown and the benchmark's return and CAGR for each portfolio and window.
- [input_manifest.json](input_manifest.json): SHA-256 digests of the code and of the committed ledgers the long-window series reproduce.

**Reproduce.**

```bash
python3 run_article_windows.py
python3 run_performance_timeseries.py
python3 -m unittest test_performance_timeseries
```

Both scripts first check the engine against the committed 30 June 2019 runs: all 1,246 long-window month-end values reproduce the committed ledgers, and each series ends on its reported total return. The test checks the saved files against those ledgers and recomputes two article-window paths.
