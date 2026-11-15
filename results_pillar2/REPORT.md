# Any prior public support screen and portfolio results

Run `python3 run_pillar2.py`. [Admission rule and limitations](../PILLAR2_METHOD.md).
This broad historical extension admits a listed candidate after captured public evidence of any qualifying named direct/subsidiary public support, however small, under an earlier industrial, technology or energy programme. No minimum size or recency is required. Completed projects remain evidence of past support; a recorded withdrawal or ownership boundary can end an event. Missing evidence is not an assumed award.

It is **not a replication of the article's specified policy streams, baskets or event dates**. The article discusses confirmed subsidies broadly, but operationally names CHIPS/IRA and EU Chips/IPCEI/France 2030/Green Deal support and illustrates June 2023 admission for Infineon and NXP. This screen instead admits both from a 2014 EnLight research project. The 31-company candidate list is retrospective and is not an exhaustive historical recipient universe. [Article](https://mitleadtrades.substack.com/p/performative-beta-trap-correcting).

## How often the screen excludes a listed company

The denominator is one observation per listed candidate per complete month from each definition's common cross-region start. An exclusion means no usable qualifying support event before the first day of that month. It does not mean that the score rejected the company or that its financial data were missing. The terminal 2 November 2026 partial return is not another company-month.

| Definition | Region | First month | Last month | Listed company-months | Excluded | Binding rate |
|---|---|---|---|---:|---:|---:|
| direct | US | 2019-06-30 | 2026-10-31 | 1,336 | 68 | 5.09% |
| direct | EU | 2019-06-30 | 2026-10-31 | 1,278 | 11 | 0.86% |
| direct | US+EU | 2019-06-30 | 2026-10-31 | 2,614 | 79 | 3.02% |
| with_indirect | US | 2019-06-30 | 2026-10-31 | 1,336 | 2 | 0.15% |
| with_indirect | EU | 2019-06-30 | 2026-10-31 | 1,278 | 0 | 0.00% |
| with_indirect | US+EU | 2019-06-30 | 2026-10-31 | 2,614 | 2 | 0.08% |

| Definition | Excluded company | Months | First excluded month | Last excluded month |
|---|---|---:|---|---|
| direct | ALFEN.AS | 11 | 2019-06-30 | 2020-04-30 |
| direct | MU | 2 | 2019-06-30 | 2019-07-31 |
| direct | TSM | 66 | 2019-06-30 | 2024-11-30 |
| with_indirect | MU | 2 | 2019-06-30 | 2019-07-31 |

Only 2 of 31 earliest direct admissions in this ledger use the article's named modern streams: GEV (Inflation Reduction Act); TSM (CHIPS Act). This counts first admissions only; a company can receive another programme later. Micron is excluded in June and July 2019; its July 1 event becomes usable in August, while new purchases wait for a quarterly review.

[Binding counts](binding_rates.csv) · [Every excluded company-month](binding_exclusions.csv) · [First-admission classification](first_admission_audit.csv).

The screen excludes very few observations. The TSMC direct-versus-indirect classification accounts for 66 US company-months; Alfen accounts for all 11 direct EU exclusions. The indirect EU coverage matches the ungated pool. The result measures accounting selection within this candidate list, not broad discrimination between firms with and without meaningful public support.

The sparse original policy ledger produces the following coverage-only start diagnostic under the engine's minimum of four scored names at a quarter-end:

| Region | First investable quarter | Covered eligible companies | First five-name quarter |
|---|---|---:|---|
| US | 2025-03-31 | 5 | 2025-03-31 |
| EU | 2023-12-31 | 4 | 2024-12-31 |

All then-eligible companies are covered at those starts and throughout the remaining monthly window. This is a diagnostic of the existing sparse ledger, whose EU records include programme participation with national funding pending; it is not a new confirmed-award reconstruction or a return backtest of the article's streams. [Diagnostic and exact eligible sets](original_ledger_start_audit.json).

## Main results: direct and subsidiary recipients

Cumulative returns include 10bp US / 15bp EU trading costs through **2 November 2026**. US returns are in USD and EU returns in EUR. Different earliest starts are not a common-period regional comparison.

| Region | Window | Start | Q50 | Q75 | Equal weight |
|---|---|---|---:|---:|---:|
| US | earliest_complete | 2019-06-30 | 378.08% | 389.82% | 699.43% |
| US | cross_region | 2019-06-30 | 378.08% | 389.82% | 699.43% |
| EU | earliest_complete | 2019-06-30 | 286.95% | 338.92% | 132.27% |
| EU | cross_region | 2019-06-30 | 286.95% | 338.92% | 132.27% |

## Sensitivity including evidenced indirect beneficiaries

Only dated company-specific supplier/customer links qualify here. These are not labeled direct awards.

| Region | Window | Start | Q50 | Q75 | Equal weight |
|---|---|---|---:|---:|---:|
| US | earliest_complete | 2019-06-30 | 400.03% | 543.26% | 739.76% |
| US | cross_region | 2019-06-30 | 400.03% | 543.26% | 739.76% |
| EU | earliest_complete | 2019-06-30 | 295.22% | 376.92% | 153.83% |
| EU | cross_region | 2019-06-30 | 295.22% | 376.92% | 153.83% |

## Why these starts

Policy evidence and data availability jointly determine the start. The engine requires at least four scored eligible companies and complete coverage of every listed policy-eligible candidate throughout the remaining window. A company is not removed merely to obtain an earlier start. No return was used to select these dates.

[Quarterly start audit](start_audit.csv) lists policy counts and every blocking company. [Monthly eligibility](monthly_eligibility.csv) distinguishes policy exclusion, listing status and missing financial/market inputs. [Every financial gap](all_financial_gaps.csv) includes pre-start periods.

- US: preceding review 2019-03-31 has 11 listed policy-eligible companies, 9 covered; missing inputs: BE|LIN. The first complete remaining window starts 2019-06-30.
- EU: preceding review 2019-03-31 has 13 listed policy-eligible companies, 9 covered; missing inputs: AMS.SW|SAF.PA|ENEL.MI|NEL.OL. The first complete remaining window starts 2019-06-30.

## Every candidate and its earliest captured admission evidence

Dates below are evidence/ownership dates, not automatic purchase dates. The first-of-month cutoff, listing restrictions, quarterly admission and financial coverage also apply. Blank means no qualifying source captured under that definition; it is not proof that a company never received support.

| Region | Company | First direct/subsidiary | Including indirect | Direct programme(s) |
|---|---|---|---|---|
| EU | AIR.PA | 2014-11-21 | 2014-11-21 | [Aerospace Technology Institute: Broughton wing manufacturing R&D](https://www.gov.uk/government/news/prime-minister-hails-1800-jobs-in-britain-at-uk-investment-summit) |
| EU | ALFEN.AS | 2020-04-13 | 2018-03-12 | [Dutch Demonstratie Energie Innovatie Tender 1: ISES, DEI1400018](https://projecten.topsectorenergie.nl/projecten/integrated-sustainable-energy-station-19011) |
| EU | AMS.SW | 2010-07-30 | 2010-07-30 | [ENIAC-JU 2009 CSI, Central Nervous System Imaging](https://www.prnewswire.com/news-releases/european-research-project-aims-to-improve-the-diagnosis-and-therapy-of-brain-diseases-99612329.html) |
| EU | ASML | 2013-11-13 | 2013-11-13 | [ENIAC Joint Undertaking E 450 EDL, grant agreement 325613](https://www.swissphotonics.net/libraries.files/ECSEL_JU_and_Photonics_Overview.pdf) |
| EU | EDF.PA | 2016-09-29 | 2016-09-29 | [Hinkley Point C Contract for Difference](https://www.edfenergy.com/energy/nuclear-new-build-projects/hinkley-point-c/news-views/contracts-signed) |
| EU | ENEL.MI | 2014-12-16 | 2014-12-16 | [FP7 GRID4EU large-scale smart-grid demonstration](https://www.enel.com/media/explore/search-news/news/2014/12/grid4eu-increasing-power-for-renewables) |
| EU | ENR.DE | 2020-09-28 | 2020-09-28 | [Horizon 2020 HYFLEXPOWER, grant 884229](https://press.siemens.com/global/en/pressrelease/hyflexpower-worlds-first-integrated-power-x-power-hydrogen-gas-turbine-demonstrator) |
| EU | IFX.DE | 2014-12-01 | 2014-12-01 | [ENIAC EnLight, Energy Efficient and Intelligent Lighting Systems](https://via.ritzau.dk/pressemeddelelse/3293310/ecsel?publisherId=90456) |
| EU | NEL.OL | 2015-07-02 | 2015-07-02 | [Akershus County Council hydrogen station public-private partnership](https://nelhydrogen.com/press-release/public-private-partnership-agreement-with-akershus-county-council-2/); [Enova hydrogen refuelling station grant](https://nelhydrogen.com/press-release/nel-to-receive-grant-from-enova-sf/); [Research Council of Norway ENERGIX: HYPER hydrogen production study](https://nelhydrogen.com/press-release/nel-asa-initiates-feasibility-partner-study-for-large-scale-hydrogen-production-in-norway/) |
| EU | NXPI | 2014-12-01 | 2014-12-01 | [ENIAC EnLight, Energy Efficient and Intelligent Lighting Systems](https://via.ritzau.dk/pressemeddelelse/3293310/ecsel?publisherId=90456) |
| EU | ORSTED.CO | 2014-11-07 | 2014-11-07 | [UK FID Enabling for Renewables: Burbo Bank Extension, Walney Extension and Hornsea 1](https://ec.europa.eu/competition/state_aid/cases/253211/253211_1583612_84_2.pdf) |
| EU | SAF.PA | 2017-10-03 | 2017-10-03 | [FP7 Clean Sky: Open Rotor / Sustainable and Green Engines](https://www.safran-group.com/pressroom/safran-celebrates-successful-start-open-rotor-demonstrator-tests-new-open-air-test-rig-southern-2017-10-03) |
| EU | STMPA.PA | 2010-07-30 | 2010-07-30 | [ENIAC-JU 2009 CSI, Central Nervous System Imaging](https://www.prnewswire.com/news-releases/european-research-project-aims-to-improve-the-diagnosis-and-therapy-of-brain-diseases-99612329.html) |
| EU | VIE.PA | 2017-11-13 | 2017-11-13 | [Horizon 2020 E2District, EE-13-2015 / grant 696009](https://openaccess.city.ac.uk/id/eprint/21943/1/proceedings-01-01105-v2.pdf) |
| EU | VWS.CO | 2018-06-28 | 2018-06-28 | [Danish EUDP: Vertical Installer wind-turbine installation technology](https://www.vestas.com/en/media/company-news/2018/vestas-and-maersk-supply-service-partner-to-lower-logis-c2963370) |
| US | AMAT | 2012-02-29 | 2012-02-29 | [DOE Building Technologies Program/NETL, US ManufacturingI solid-state lighting](https://www1.eere.energy.gov/buildings/publications/pdfs/ssl/2012_ssl_project_portfolio.pdf) |
| US | BE | 2018-06-12 | 2018-06-12 | [Delaware Strategic Fund manufacturing and employment incentive](https://www.sec.gov/Archives/edgar/data/1664703/000119312518190488/d96446ds1.htm) |
| US | ENPH | 2010-03-31 | 2010-03-31 | [California Energy Commission Public Interest Energy Research grant to SolarTech, Santa Clara University and Enphase](https://www.nrel.gov/docs/fy10osti/47866.pdf) |
| US | ETN | 2011-03-18 | 2011-03-18 | [DOE-funded Eaton/HP energy-efficient water-cooled IT rack research](https://www.eaton.com/content/dam/eaton/company/investor-relations/2010-Annual-Report.pdf) |
| US | FSLR | 2011-02-28 | 2011-02-28 | [ARRA Section 48C advanced energy manufacturing tax credit: Perrysburg manufacturing expansion](https://www.sec.gov/Archives/edgar/data/1274494/000127449411000007/fslrdec1010k.htm) |
| US | GEV | 2024-04-02 | 2024-04-02 | [Inflation Reduction Act advanced manufacturing production credits for the Wind business](https://www.gevernova.com/sites/default/files/2024-02/form10_registration_statement_feb2024.pdf) |
| US | GFS | 2021-10-04 | 2011-09-27 | [Empire State Development semiconductor-fab investment grants](https://www.sec.gov/Archives/edgar/data/1709048/000119312521290644/d192411df1.htm) |
| US | INTC | 2014-08-26 | 2011-09-27 | [Oregon Strategic Investment Program, existing 2005 Intel agreement](https://www.washingtoncountyor.gov/cao/news/key-economic-vote-city-and-county) |
| US | LIN | 2018-10-31 | 2018-10-31 | [DOE Advanced Manufacturing Office: Novomer/Praxair conversion of carbon dioxide to chemicals](https://www.energy.gov/cmei/ammto/articles/amo-success-story-converting-waste-valuable-materials-and-chemicals) |
| US | LRCX | 2016-01-22 | 2016-01-22 | [California Employment Training Panel, ET 16-0304](https://etp.ca.gov/wp-content/uploads/sites/70/2021/08/ETP_PanelPacket-January2016.pdf) |
| US | MCHP | 2017-04-04 | 2017-04-04 | [Oregon/Gresham Strategic Investment Program and Zone](https://gresham.granicus.com/MetaViewer.php?clip_id=445&meta_id=42542&view_id=2) |
| US | MU | 2019-07-01 | 2019-07-01 | [Virginia Semiconductor Manufacturing Grant Fund](https://legacylis.virginia.gov/cgi-bin/legp604.exe?191+ful+CHAP0041+pdf=); [CHIPS Incentives Program, Idaho and New York DRAM projects](https://content.govdelivery.com/accounts/USDOC/bulletins/3c6799f) |
| US | NEE | 2011-08-29 | 2011-08-29 | [DOE Title XVII Section 1705 Financial Institution Partnership Program: Genesis Solar](https://newsroom.nexteraenergy.com/NextEra-Energy-Resources-subsidiary-closes-on-935-million-financing-and-secures-a-DOE-loan-guarantee-for-its-Genesis-solar-project) |
| US | PLUG | 2011-05-09 | 2011-05-09 | [DOE ARRA fuel-cell market transformation grants: combined heat and power and backup power](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review11/h2pn06_devlin_mt_and_arra_2011_o.pdf) |
| US | TSM | 2024-11-15 | 2011-09-27 | [CHIPS Incentives Program, TSMC Arizona leading-edge fabs](https://content.govdelivery.com/accounts/USDOC/bulletins/3c1ec14) |
| US | TXN | 2019-04-18 | 2004-11-03 | [Texas Enterprise Fund, Richardson 300 mm fab](https://gov.texas.gov/news/post/governor-abbott-announces-texas-instruments-new-300mm-facility-in-richardson) |

## Award amounts and the Alfen boundary

Amounts do not affect admission, ranks or weights. Each event records a company amount and currency when established, or an explicit unknown/project-total-only status. Ceilings, conditional commitments, recognized credits and lower bounds retain separate labels. Consortium costs, public contributions and third-party awards are not assigned to each company. Missing amounts are null, never zero. [All event amounts and evidence](award_amounts.csv).

- Lam Research: USD48,816 approved California training contract. [State release](https://www.labor.ca.gov/wp-content/uploads/sites/338/2019/07/ETPPressRelease-January2016.pdf).
- Texas Instruments: USD5,124,000 TEF commitment conditional on investment and staffing; no payment is inferred. [Governor release](https://gov.texas.gov/news/post/governor-abbott-announces-texas-instruments-new-300mm-facility-in-richardson).
- Infineon and NXP: EUR41.3m is the total EnLight cost across 27 partners, only partly publicly funded. Individual company awards and the total public contribution are unknown. [ECSEL release](https://via.ritzau.dk/pressemeddelelse/3293310/ecsel?publisherId=90456).

Alfen's March 2018 prospectus reports EUR968,000 of 2017 government-grant income for an African solar/storage system, but the captured passage does not identify the grantor or programme. The later DEI ISES record names Alfen and a EUR2,776,119 project grant; its final-report publication is dated 13 April 2020. The descriptions plausibly concern the same project, but that does not establish that the Dutch grantor/programme was publicly identifiable in March 2018. The existing 2020 direct-admission boundary is retained as an unresolved evidence/classification choice, not a claim that Alfen received no earlier public support. Separately evidenced SDE+ customer exposure admits it in the indirect panel. [2018 prospectus, note 9](https://live.euronext.com/sites/default/files/amco-9819704-v1-prospectus_alfen_n_v__dated_12_march_2018_including_e-disclaimer.pdf) · [DEI registry](https://projecten.topsectorenergie.nl/projecten/integrated-sustainable-energy-station-19011).

[All-candidate audit and unresolved questions](candidate_audit.csv) · [Source-linked event ledger](events_normalized.json) · [Policy events supporting every holding](holdings_policy_links.csv).

## Matched financial-timing comparison

The financial delay uses 180/90-day availability floors and 730/365-day freshness; policy dates stay unchanged. Each definition starts both financial treatments together when coverage is complete. Equal-weight monthly NAVs are asserted identical within each region/definition.

| Definition | Region | Start | Timing | Q50 | Q75 | Equal weight |
|---|---|---|---|---:|---:|---:|
| direct | US | 2019-09-30 | source | 332.19% | 285.42% | 691.80% |
| direct | US | 2019-09-30 | delay_adjusted | 367.37% | 315.69% | 691.80% |
| direct | EU | 2019-09-30 | source | 248.97% | 320.05% | 110.54% |
| direct | EU | 2019-09-30 | delay_adjusted | 223.19% | 222.87% | 110.54% |
| with_indirect | US | 2019-09-30 | source | 343.55% | 430.54% | 720.69% |
| with_indirect | US | 2019-09-30 | delay_adjusted | 401.86% | 369.03% | 720.69% |
| with_indirect | EU | 2019-09-30 | source | 257.50% | 343.45% | 127.53% |
| with_indirect | EU | 2019-09-30 | delay_adjusted | 206.51% | 203.99% | 127.53% |

## Validation and remaining limits

48 runs pass policy/source cutoffs, complete eligible coverage, listing and cost/holdings/NAV checks. All 31 candidates have a research record. Six ungated headline results reproduce; 3067 earlier input/result files remain byte-identical.

This adds the dated admission gate to the existing two accounting signals. It does not add subsidy utilization, full six-factor scoring, fixed sector baskets or Pillar 3 network scores. Earlier adjusted prices and the retrospective candidate list retain the limitations documented in the longer-history report. The earliest captured evidence is a conservative research boundary, not a claim that every earlier archive has been exhausted.

There is no minimum award-size threshold. Small targeted research/training awards can establish eligibility; that does not establish material or continuing earnings support. Public infrastructure and university benefits are classified as indirect unless company receipt or ownership is documented.

[Why US/EU results differ](ATTRIBUTION.md) · [Summary with CAGR/volatility/drawdown](summary.csv) · [Active-return statistics](active_statistics.csv) · [Year returns](year_returns.csv) · [Validation](validation.json) · [Input hashes](input_manifest.json).
