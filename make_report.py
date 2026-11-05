#!/usr/bin/env python3
"""Optional presentation export. Requires reportlab and matplotlib."""
import argparse,csv,json
from pathlib import Path
from xml.sax.saxutils import escape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime as dt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT,TA_RIGHT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from matplotlib import font_manager

pdfmetrics.registerFont(TTFont('ReportSans',font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'))))
pdfmetrics.registerFont(TTFont('ReportSans-Bold',font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',weight='bold'))))
pdfmetrics.registerFontFamily('ReportSans',normal='ReportSans',bold='ReportSans-Bold',italic='ReportSans',boldItalic='ReportSans-Bold')

ROOT=Path(__file__).resolve().parent
D=json.loads((ROOT/'tables_actual/workbook_data.json').read_text())
INK='#17324D';BLUE='#245F99';GREEN='#35796A';GRAY='#566573'
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle',fontName='ReportSans-Bold',fontSize=23,leading=27,textColor=colors.HexColor(INK),spaceAfter=13))
styles.add(ParagraphStyle(name='Section',fontName='ReportSans-Bold',fontSize=15,leading=18,textColor=colors.HexColor(INK),spaceAfter=10))
styles.add(ParagraphStyle(name='Body',fontName='ReportSans',fontSize=9.3,leading=13,spaceAfter=8,textColor=colors.HexColor('#273746')))
styles.add(ParagraphStyle(name='SmallBody',fontName='ReportSans',fontSize=8,leading=11,spaceAfter=6,textColor=colors.HexColor(GRAY)))
styles.add(ParagraphStyle(name='TableHead',fontName='ReportSans-Bold',fontSize=8,leading=10,textColor=colors.white))
styles.add(ParagraphStyle(name='TableCell',fontName='ReportSans',fontSize=8,leading=10))
def P(t,style='Body'):return Paragraph(t,styles[style])
def pct(x):return f'{x:.2%}'
def table(headers,rows,widths,small=False):
    data=[[P(str(h),'TableHead') for h in headers]]
    data += [[P(escape(str(v)),'TableCell') for v in row] for row in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(INK)),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),4 if small else 6),('BOTTOMPADDING',(0,0),(-1,-1),4 if small else 6),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F1F4F7')]),
        ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor(INK)),
        ('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#CBD5DF'))]))
    return t
def summary(region,panel,rule,window='matched'):
    return next(s for s in D['all_experiments'] if s['region']==region and s['panel']==panel and s['rule']==rule and s['window']==window)
def read(p):return list(csv.DictReader(p.open()))
def make_chart(out):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,1,figsize=(8,7.5),layout='constrained')
    for ax,reg in zip(axs,['US','EU']):
        for rule,col in [('q75',BLUE),('q50',GREEN),('equal','#88714F')]:
            s=summary(reg,'actual_expanded',rule);rs=read(ROOT/'results_actual'/s['run']/'monthly.csv')
            days=[dt.date.fromisoformat(r['date']) for r in rs]+[dt.date.fromisoformat(s['latest_end'])]
            nav=[float(r['NAV']) for r in rs]+[s['final_NAV']]
            ax.plot(days,nav,label='Covered universe control' if rule=='equal' else rule.upper(),color=col,lw=1.8,ls='--' if rule=='equal' else '-')
            if rule=='q75':ax.plot(days,[float(r['BenchmarkNAV']) for r in rs]+[s['final_benchmark_NAV']],label='ETF benchmark mix',color='#9A9DA1',lw=1.5)
        ax.set_title(reg+' expanded hybrid | start '+s['start'],loc='left',fontweight='bold',color=INK,pad=10)
        ax.set_ylabel('NAV, initial capital = 100');ax.grid(axis='y',alpha=.18);ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.legend(loc='upper left',frameon=False,ncol=2,fontsize=8)
    fig.savefig(out,dpi=170);plt.close(fig)
def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#CCD5DD'));c.line(40,35,A4[0]-40,35)
    c.setFont('ReportSans',8);c.setFillColor(colors.HexColor(GRAY))
    c.drawString(40,22,'Alpaca ETF research | Actual dates and interim coverage | 4 Nov 2026')
    c.drawRightString(A4[0]-40,22,str(doc.page))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(ROOT.parent/'outputs/actual_dates_20261104/Actual_Dates_Backtest_Report.pdf'));a=ap.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);chart=out.parent/'NAV_Comparison.png';make_chart(chart)
    story=[P('Actual dates.<br/>Broader financial coverage.','ReportTitle'),
        P('US and European ETF backtests, through 2 November 2026','Section'),
        P('The two requested changes are implemented: evidenced publication dates and more original interim statements. The one-quarter entry/exit rule, 1-9 holding bounds, monthly weighting and existing tilt are preserved. No momentum or new position sizing was added.'),
        P('<b>Evidence:</b> 333 original financial observations produce 310 complete annual/TTM inputs. Interim coverage increases from nine names to 15. Original financial inputs are verified for <b>18 of the 31 candidates</b>; the remaining 13 are excluded and identified on page 4.'),
        P('Matched-window results','Section')]
    panels={'annual':'Annual','original9':'Hybrid, original 9','expanded':'Hybrid, expanded'}
    rr=[[s['Region'],panels[s['Panel']],s['Entry'],pct(s['Total_return']),pct(s['CAGR']),pct(s['Monthly_drawdown'])] for s in D['summary']]
    story += [table(['Region','Financial panel','Entry','Total return','CAGR','Monthly drawdown'],rr,[50,126,43,90,85,121],True),
        Spacer(1,10),P('US: 30 Sep 2022 to 2 Nov 2026. Europe: 30 Sep 2021 to 2 Nov 2026. Net of 10/15 bps per bought or sold dollar. US values are in USD; Europe in EUR. These two windows should not be treated as a direct cross-region comparison.','SmallBody'),
        P('<b>Benchmark context.</b> The expanded US portfolios beat both the ETF mix (139.63%) and covered-universe control (148.75%). The European portfolios beat the ETF mix (10.18%) but lag the covered-universe control (89.02%).'),
        P('<b>Interpretation.</b> Broader data improved Q50 returns and reduced Q75 returns on these windows. The highest return among the actual-date US variants was the original-nine hybrid Q75 at 218.50%. This is an in-sample result, not evidence that its narrower data coverage is preferable.'),
        P('Prices and FX remain frozen at the prior 2 Nov endpoint to isolate financial-data effects. The report does not include 3-4 Nov returns. Full monthly histories, all 114 experiments, quarterly paper tables and source records accompany this report.','SmallBody'),PageBreak(),
        P('Separate timing from coverage','ReportTitle'),
        P('The timing comparison holds the original financial numbers fixed. Its delayed control waits until the later of actual release or 180 days after annual fiscal end / 90 days after interim end. Neither treatment uses information before publication.'),
        table(['Region','Panel','Entry','Delayed return','Actual dates','Change (pp)'],
            [[r['Region'],panels[r['Panel']],r['Entry'],pct(r['Delayed_return']),pct(r['Actual_date_return']),f"{r['Change_percentage_points']:+.2f}"] for r in D['timing']],
            [50,126,43,96,96,104],True),Spacer(1,14),
        P('Effect of expanding interim coverage','Section'),
        table(['Region','Entry','Original 9','Expanded','Change (pp)'],[[r['Region'],r['Entry'],pct(r['Original9_return']),pct(r['Expanded_return']),f"{r['Change_percentage_points']:+.2f}"] for r in D['coverage_effect']],[60,60,130,130,135]),
        Spacer(1,12),P('Earlier availability helped all matched US variants and hurt all European variants. Faster information changes which reports pass the cutoff, company ranks, eligibility and entry/exit paths; it does not mechanically improve returns. Expanding coverage changes the same cross-sectional ranks even when the companies already had annual observations.'),
        P('In the expanded portfolios, Micron was the largest US profit contributor: +119.16 and +109.75 percentage points for Q75 and Q50. GlobalFoundries contributed -43.60 and -41.48 points; Enphase -30.53 and -26.53. ASML led European contributions (+38.57 / +32.66), while STMicroelectronics detracted (-15.79 / -11.25). These are dollar P&amp;L contributions per 100 initial capital, not causal explanations of corporate performance.'),
        P('Comparisons with the old vendor-based runs combine source-vintage, timing and coverage changes. Separate matched-date legacy comparisons are supplied in the workbook and CSV tables.','SmallBody'),PageBreak(),
        P('Growth of invested capital','ReportTitle'),
        P('Expanded hybrid, actual publication dates. The selected portfolios retain the inherited equal-weight-plus-tilt rule; the covered-universe control holds all eligible covered candidates. Monthly observations are shown, with the observed 2 Nov endpoint.'),
        Image(str(chart),width=510,height=478),
        P('The control is not an equal-weight copy of exactly the selected ETF holdings. Normal additions occur quarterly, with monthly reweighting and coverage removals. It can hold more than nine stocks. Benchmark mixes are frictionless and monthly rebalanced, as in the inherited specification.','SmallBody'),
        P('Earliest feasible actual-date histories begin 31 March 2021. Expanded Q75/Q50 total returns on that longer window are 179.15% / 164.57% for the US and 77.66% / 68.28% for Europe. Different start dates materially change results; the accompanying tables keep earliest, matched and cross-region windows separate.'),PageBreak(),
        P('What is actually covered','ReportTitle'),
        P('Counts are complete scoring inputs. An issuer report may be captured without supplying enough components to form a full TTM observation. A zero below means no usable input captured here, not a reported financial zero.'),
        table(['Region','Ticker','Company','Annual','TTM','Latest period'],
            [[r['Region'],r['Ticker'],r['Company'],r['Annual_inputs'],r['TTM_inputs'],r['Latest_period'] or 'Unavailable'] for r in D['coverage']],
            [45,65,195,45,40,125],True),
        Spacer(1,8),P('Totals: 103 annual and 207 TTM inputs. Annual-only coverage: EDF, Enel and Veolia. Fifteen issuers have at least one complete interim TTM input, with gaps varying by company and year. Financial dates can be as early as FY2019, but a portfolio requires at least four covered eligible names.','SmallBody'),PageBreak(),
        P('Method, replication and limits','ReportTitle')]
    paras=[
        ('Availability','Each financial observation has an actual period end, publication date, source URL and component IDs. All components must predate the first day of the rebalance month. Annual records remain usable for at most 550 days and interim records for 275 days from fiscal end. October releases first enter the modeled information set for November month-end.'),
        ('Observed arithmetic','TTM values use reported TTM, original annual plus current YTD minus comparable prior YTD, comparable quarter differences, or four observed consecutive quarters. No missing value is filled, no quarter is multiplied by four, and no revised-vendor fallback is allowed in actual-date runs. Original observations and arithmetic ledgers are supplied.'),
        ('Score and trading','The reduced score combines ranked operating income / (assets - current liabilities) and inverse cash accruals (net income - operating cash flow) / assets, with normalized 25:12 weights. Q75/Q50 entry and Q25 exit need one qualifying quarter. Normal membership changes quarterly; scores and weights update monthly. Forced coverage exits and floor admissions are separately logged.'),
        ('What remains unresolved','Only 18 of 31 retrospective candidates have complete original inputs here. The universe is not historically reconstructed from policy decisions. Full subsidy, capex, analyst, governance, lobbying and network/IP factors remain unobserved. Current hosted original-year reports are not a certified archive of every first-published version. US GAAP/IFRS classification and restatements are not comprehensively harmonized.'),
        ('Measurement','CAGR uses actual elapsed calendar time. Arithmetic Sharpe assumes zero risk-free rate; the paper-style CAGR/volatility ratio is separately labeled. Volatility and drawdown use full monthly observations, not a complete daily risk history. Relative wealth alpha is strategy NAV / benchmark NAV - 1. Returns omit fund management fees, taxes and market impact beyond stated bps.'),
        ('Replication','Run python3 run_all.py inside the extracted package using Python 3.10+. No network, API key or third-party Python package is required for the core run. It recreates source arithmetic, 114 runs, validations, CSV and LaTeX tables from frozen inputs. Changing portfolio rules requires rerunning Python; the workbook is a review export.')]
    for h,t in paras:story.append(P('<b>'+h+'.</b> '+t))
    story += [table(['Validation','Records'],[[r['check'],str(r['records'])] for r in D['validation']],[405,110],True),
        Spacer(1,8),P('Underlying financial evidence: dated original issuer releases/filings; market data: inherited public adjusted-price and FX observations, with source URLs in the package. No generated data are used. Monthly snapshots are reconstructed retrospectively; issuers themselves report quarterly or annually.','SmallBody')]
    for reg in ['US','EU']:
        for rule in ['q75','q50']:
            s=summary(reg,'actual_expanded',rule)
            qs=[q for q in D['quarterly'] if q['Region']==reg and q['Panel']=='actual_expanded' and q['Entry']==rule.upper()]
            story += [PageBreak(),P(reg+' expanded hybrid '+rule.upper(),'ReportTitle'),
                P('Paper-style quarterly performance','Section'),
                P(s['start']+' to '+s['latest_end']+'. Initial capital 100; net of trading costs. Alpha means relative wealth. The initial deployment quarter and incomplete final quarter are marked with an asterisk.','SmallBody'),
                table(['Quarter','ETF NAV','ETF cum.','Bench NAV','Bench cum.','Alpha','Stocks'],
                    [[q['Quarter']+('*' if q['Partial_quarter'] else ''),f"{q['ETF_NAV']:.2f}",pct(q['ETF_Cum_Return']),f"{q['Bench_NAV']:.2f}",pct(q['Bench_Cum_Return']),pct(q['Alpha_ETF_div_Bench_minus1']),q['Holdings']] for q in qs],
                    [67,72,80,77,80,77,62],True),Spacer(1,15),
                table(['Paper summary metric','Value'],[[label,pct(s[key]) if key not in ('Sharpe_rf0_monthly','Paper_CAGR_div_vol') else f"{s[key]:.3f}"] for label,key in [
                    ('ETF total return','total_return'),('ETF annualized return','CAGR'),('Benchmark annualized return','benchmark_CAGR'),
                    ('Cumulative alpha (relative wealth)','relative_alpha'),('Sharpe, arithmetic monthly, rf=0','Sharpe_rf0_monthly'),
                    ('Paper-style CAGR / volatility','Paper_CAGR_div_vol'),('Maximum drawdown, monthly','max_drawdown_monthly')]], [350,165],True),
                Spacer(1,9),P('Benchmark alpha against itself is identically zero; that column is retained in the CSV/workbook. Complete score tables and all monthly/quarterly ledgers are supplied. Unobserved original-paper factors are labeled unavailable and never inserted as zero.','SmallBody')]
    doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=38,bottomMargin=48,title='Actual publication dates and expanded financial coverage',author='Alpaca ETF research')
    doc.build(story,onFirstPage=footer,onLaterPages=footer);print(out)
if __name__=='__main__':main()
