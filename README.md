# Une Baguette Fromage 🥖🧀

This writeup shares the strategies, infrastructure, insights, and research process that brought us to 4th place globally and 1st place in Europe in IMC Prosperity 4 (2026). Competing against 18.803 teams worldwide, we achieved a final score of 1,386,318 XIRECS.

<table width="80%">
  <tbody>
    <tr>
      <td align="center" valign="top" width="200px">
          <img src="https://media.licdn.com/dms/image/v2/D4D03AQEvZtqmWS4Ayw/profile-displayphoto-scale_400_400/B4DZlAHehLJUAg-/0/1757717326710?e=1779926400&v=beta&t=cpMRrQrCbMzoEjftBtRdUAV6W7KU8IY-Y0t8KdbJNGw" width="150;" alt="Member"/>
          <br />
          <p><b>Jasper van der Ende</b></p>
      </td>
      <td align="center" valign="top" width="200px">
          <img src="https://media.licdn.com/dms/image/v2/D4D03AQGBA1y9hLNDNw/profile-displayphoto-scale_400_400/B4DZ1qSih7GUAg-/0/1775604744014?e=1779926400&v=beta&t=1aU1N7w7XNwdf2e-7f13HhT8Mhqu2ljbEAM2x2p1bwg" width="150;" alt="Member"/>
          <br />
          <p><b>Teun Schuur</b></p>
      </td>
      <td align="center" valign="top" width="200px">
          <img src="https://media.licdn.com/dms/image/v2/D4E03AQHLffcFLPo9Mg/profile-displayphoto-scale_400_400/B4EZmBF4BPIUAo-/0/1758807426039?e=1779926400&v=beta&t=vJs0WG6DC95fBsGdLsy_G4nJQd5VG19gFUiRk1963dw" width="150;" alt="Member"/>
          <br />
          <p><b>Thomas St Ges</b></p>
      </td>
      <td align="center" valign="top" width="200px">
          <img src="https://media.licdn.com/dms/image/v2/D4D03AQHOkN4WqXVMkA/profile-displayphoto-shrink_400_400/B4DZWgAe2QGkAg-/0/1742146236331?e=1779926400&v=beta&t=SWSTkpveg75vrcadbhZNWjZkH6lbHYYlry06tUYRe4o" width="150;" alt="Member"/>
          <br />
          <p><b>Guilhem Doat</b></p>
      </td>
      <td align="center" valign="top" width="200px">
          <img src="https://media.licdn.com/dms/image/v2/D4E03AQHsPSymykl1-A/profile-displayphoto-scale_400_400/B4EZ2shB5bKEAk-/0/1776715833813?e=1779926400&v=beta&t=gbDDhrzElkxz3JTgXKTmglzyaQN9OVV89ggpWRAuyCo" width="150;" alt="Member"/>
          <br />
          <p><b>Dylan Conrad</b></p>
      </td>
    </tr>
  </tbody>
</table>

<br/>

As many top-performing teams from previous Prosperity iterations have done, we decided to publish this writeup to give back to the Prosperity community.

We believe Prosperity is one of the rare competitions where sharing approaches genuinely raises the bar for everyone. Every public writeup forces future participants — and IMC itself — to push the limits further. Previous teams’ writeups helped us tremendously during the competition, so this document is our attempt to continue that cycle.

That said, getting to the top was not just about getting lucky and finding a magical strategy. We systematically tested every possibility we could think of, building our own understanding of the markets IMC had created instead of blindly applying textbook techniques.

Our goal with this document is not only to explain what worked, but also:
- how we approached research,
- how we validated ideas,
- how we avoided overfitting,
- and how we navigated an absurdly large search space under extreme time pressure.

<br/>

## IMC Prosperity 4

IMC Prosperity 4 (2026) was a global algorithmic trading competition consisting of multiple rounds across several weeks, with more than 22,000 teams participating worldwide.

Participants developed trading algorithms to maximize profits against simulated markets populated by various bots and hidden behaviors. Over the course of the competition, new products and mechanics were gradually introduced, forcing teams to constantly adapt their strategies and research process.

The competition touched many areas of quantitative trading and research:
- market making,
- statistical arbitrage,
- microstructure analysis,
- derivatives pricing,
- signal extraction,
- event-based trading,
- optimization,
- and game theory.

Each round also featured a separate manual challenge involving probabilistic reasoning, auctions, optimization, or strategic decision-making.

<br/>

## Structural Overview

- [Tools & Infrastructure](#tools--infrastructure)
- [Wall Mid](#wall-mid)
- [On Vibe Coding](#on-vibe-coding)
- [Algorithmic Challenge](#algorithmic-challenge)
  - [Round 1](#round-1)
  - [Round 2](#round-2)
  - [Round 3](#round-3)
  - [Round 4](#round-4)
  - [Round 5](#round-5)
- [Manual Challenge](#manual-challenge)
- [FAQ](#faq)

<br/>

# Tools & Infrastructure

One of our earliest decisions was to make sure we did not rely solely on the native IMC tester.

Instead, we forked and heavily extended Jmerle’s backtester and visualizer for Prosperity 4.

Having a proper local environment was absolutely essential for us, especially because the round timers were brutal:
- 72 hours per round during qualifications
- 48 hours per round during finals

This leaves very little room for slow feedback loops.

The backtester gave us:
- local exchange simulation,
- position limits,
- fair value updates,
- trader replay,
- and rapid parameter testing

without needing to constantly submit to the official platform.

Being able to run hundreds of local simulations in minutes instead of waiting on the website queue was a massive advantage.

<br/>

## Dashboard

On top of the core backtester, we built a heavily customized dashboard environment.

<table>
<tr valign="top">
<td width="100%" align="center">
  <strong>Figure 1: Dashboard Overview</strong>
</td>
</tr>

<tr valign="top">
<td width="100%" align="center">
  <img src="IMAGE_URL"
       alt="Dashboard"
       width="100%" />
</td>
</tr>

<tr valign="top">
<td width="100%" align="center">
  <em>Overview of the custom visualization dashboard used throughout the competition.</em>
</td>
</tr>
</table>

Key additions included:
- Price and mid-price charts with fair value overlays
- Volume profiles per product and timestamp
- PnL attribution broken down per product
- Visualization of counterparty trades
- Position tracking over time
- Dynamic graphing support for arbitrary indicators

The dashboard became one of our most important research tools throughout the competition.

We used it constantly for:
- validating hypotheses,
- spotting hidden behaviors,
- understanding microstructure,
- and debugging strategies.

<br/>

## Jupyter Workflow

Alongside the dashboard, we relied heavily on Jupyter notebooks.

The notebooks acted as our scratchpad for:
- exploratory analysis,
- signal research,
- residual analysis,
- autocorrelation testing,
- parameter optimization,
- and visualization.

We found the separation between:
- notebooks for fast experimentation,
- and the dashboard for validation

to be extremely effective.

<br/>

## Git Workflow

We also maintained a lightweight git branching structure.

Each product family had its own branch, while the main branch only received tested competition-ready code.

This prevented the classic Prosperity failure mode:
fixing one product at 3AM and accidentally breaking another one.

Version discipline ended up saving us repeatedly during later rounds.

<br/>

## A Note on Backtester Limitations

One thing we want to stress:

Local backtesting has real structural limitations.

Ignoring them leads directly to overfit strategies that look incredible locally and collapse live.

The most important limitations we encountered were:
- No market impact
- Simplified orderbook dynamics
- Imperfect bot behavior replication

Our philosophy became:

> Use the backtester as a filter, not as ground truth.

If a strategy failed locally, we discarded it.

If it passed locally, we still questioned it aggressively before trusting it live.

Strategies with absurdly good backtests were usually overfit.

<br/>

# Wall Mid

One of the most important concepts throughout the competition was what we called the **Wall Mid**.

The standard midpoint between best bid and best ask was often a terrible estimate of actual fair value.

This was because:
- bots aggressively overbid,
- undercutting constantly occurred,
- and top-of-book prices were noisy.

During testing on the official Prosperity platform, it became possible to indirectly infer the underlying fair value through unrealized PnL changes.

Buying or selling tiny amounts and observing resulting PnL changes gave clues about where the simulator itself considered fair value to be.

We found that the best estimate consistently came from large persistent liquidity walls deeper in the book.

These walls:
- remained stable,
- appeared highly informed,
- and often anchored around the simulator’s internal fair value.

So instead of using the naive midpoint, we:
1. identified dominant liquidity walls,
2. extracted bid and ask wall prices,
3. and took the midpoint between those levels.

This produced a significantly cleaner and more predictive estimate of fair value.

<table>
<tr valign="top">
<td width="100%" align="center">
  <strong>Figure 2: Wall Mid vs Raw Mid</strong>
</td>
</tr>

<tr valign="top">
<td width="100%" align="center">
  <img src="IMAGE_URL"
       alt="Wall Mid"
       width="100%" />
</td>
</tr>

<tr valign="top">
<td width="100%" align="center">
  <em>Comparison between noisy top-of-book midpoint and Wall Mid estimation.</em>
</td>
</tr>
</table>

<br/>

# On Vibe Coding

We want to be honest about something that rarely makes it into writeups:

A significant portion of our tooling and research was built through what the community now calls **vibe coding**.

Fast, iterative, heavily AI-assisted development became one of the most important tools during the competition.

In a competition like Prosperity, you simply cannot afford to spend:
- six hours architecting perfect pipelines,
- writing elegant abstractions,
- or polishing infrastructure

when there are only 30 hours left in a round.

The correct move is often:
1. get something working quickly,
2. validate the idea,
3. then decide whether it deserves cleanup.

Concretely, this included:
- rapidly prototyping parsers,
- building one-off scanners,
- dynamically extending the dashboard,
- generating parameter sweep harnesses,
- and quickly validating statistical ideas.

The key discipline is knowing:
- when AI-generated code is acceptable,
- and when every line must be manually verified.

We kept a strict separation:
- exploratory tooling could be messy,
- production strategy code had to be understood completely.

Used correctly, vibe coding became an enormous force multiplier.

<br/>

# Algorithmic Challenge

## Round 1

### OSMIUM

The first product introduced was ASH_OSMIUM_OSMIUM (which we will simply call OSMIUM).

OSMIUM was essentially:
- large spread,
- slowly mean reverting,
- and highly suitable for market making.

After performing an Augmented Dickey-Fuller test, we confirmed the product was stationary around approximately 10,000.

<table>
<tr valign="top">
<td width="100%" align="center">
  <strong>Figure 3: OSMIUM Orderbook</strong>
</td>
</tr>

<tr valign="top">
<td width="100%" align="center">
  <img src="IMAGE_URL"
       alt="OSMIUM"
       width="100%" />
</td>
</tr>

<tr valign="top">
<td width="100%" align="center">
  <em>Typical OSMIUM orderbook behavior.</em>
</td>
</tr>
</table>

#### Empty Book Behavior

One of the first major discoveries was what happened when one side of the book became empty.

This occurred approximately 8% of the time.

We tested increasingly aggressive quotes and discovered that:
- a spread of roughly 100 around previous Wall Mid
- maximized profitability
- while still reliably getting filled.

This alone generated enormous expected value.

#### Final Strategy

Our OSMIUM strategy became a relatively standard Avellaneda-Stoikov style market maker with inventory management.

The reserve price shifted linearly with inventory:

S_r = 10000 - γQ

where:
- Q = inventory
- γ controlled inventory pull strength

We found γ = 1/12 to perform best.

The strategy:
- penny quoted around fair value,
- crossed spread when sufficiently favorable,
- and widened aggressively when one side became empty.

<br/>

### INTARIAN_PEPPER_ROOT

PEPPER_ROOT behaved very differently.

Unlike OSMIUM, it increased almost deterministically by approximately 0.1 per tick.

The obvious strategy was simply:
> buy and hold

However, because the spread remained large, market making was still profitable.

This created a more interesting optimization problem.

#### Dynamic Programming Model

We modeled the problem using dynamic programming.

The Bellman equation optimized expected future value over:
- inventory states,
- spread distributions,
- and trade size probabilities.

This allowed us to calculate:
- optimal bid thresholds,
- optimal ask thresholds,
- and inventory-dependent quoting behavior.

The initial implementation underperformed slightly due to several hidden assumptions.

To compensate, we introduced:
- bid adjustment parameters,
- ask adjustment parameters,
- and optimized them through parameter sweeps.

This was not mathematically elegant.

But it worked.

<br/>

## Round 2

### Extra Market Access

Round 2 introduced the ability to bid for “extra market access.”

The catch:
- extra access only increased quotes,
- not actual trading opportunities.

This was an intentional red herring.

Why would one pay for:
> more competition against other market makers?

The obvious answer became:
> bid zero.

<br/>

### Recurring Takers

During the intermission period following Round 2, we performed broader research into generalized alpha sources.

This led to one of our most interesting discoveries.

Across both OSMIUM and PEPPER:
- takers frequently reappeared
- at identical timestamps
- with identical size and direction
- on consecutive days.

We eventually identified the underlying mechanism:

If a taker appeared at:
- timestamp t
- on day d

then there was a very high probability the same taker appeared again:
- at timestamp t
- on day d+1

This effect became extremely strong for larger orders.

For OSMIUM:
- takers with size ≥ 7
- repeated with ~97.7% probability.

#### Monetizing This

The alpha came from exploiting Prosperity’s matching engine mechanics.

If we predicted a large taker would arrive:
1. we cleared all existing liquidity,
2. leaving one side empty,
3. then placed an extreme quote,
4. which the taker would often immediately hit.

This effectively recreated hidden-taker opportunities.

<br/>

## Round 3

### HYDROGEL_PACK

HYDROGEL_PACK behaved similarly to OSMIUM:
- slowly mean reverting,
- stable spread,
- and consistently liquid.

The product was relatively straightforward compared to what came next.

<br/>

### VELVETFRUIT_EXTRACT

VELVETFRUIT_EXTRACT was significantly more volatile.

A simple Avellaneda-Stoikov market maker no longer worked well due to:
- tighter spreads,
- larger jumps,
- and higher short-term volatility.

We instead modeled the product as an Ornstein-Uhlenbeck process.

Estimated parameters:
- mean ≈ 5250
- theta ≈ 0.15
- sigma ≈ 9.8

This implied long-term volatility of approximately 18.

This became our primary threshold.

#### Final Strategy

The resulting strategy became extremely simple:
- buy below 5232
- sell above 5268

Despite its simplicity, this performed surprisingly well.

<br/>

### Options

Round 3 also introduced 10 call options written on VELVETFRUIT_EXTRACT.

Initially, we expected IV surface trading opportunities similar to Prosperity 3.

However, analysis revealed:
- implied volatility remained almost constant,
- per option,
- throughout each day.

This completely destroyed the standard:
> fit parabola → trade IV mispricing

approach.

Instead, we concluded:
> the options were essentially priced fairly.

Therefore:
- the options themselves contained little standalone alpha,
- but they could still be used to leverage mean reversion exposure on the underlying.

The resulting thresholds were computed through:
- Black-Scholes pricing,
- combined with OU thresholds.

<br/>

## Round 4

### Mark Analysis

Round 4 introduced trader marks.

Several marks quickly emerged as highly important:
- Mark 14,
- Mark 38,
- Mark 55,
- Mark 22,
- and Mark 01.

One relationship dominated the round:
> Mark 14 versus Mark 38.

Approximately:
- 60% of HYDROGEL flow
- came from this interaction.

#### Machine Learning Experiments

We performed significant ML research during this round.

Most generalized:
- Mark-conditioned path-max strategies

looked incredible offline.

However:
- almost all collapsed when translated into real-time rules.

One exception survived:
- a focused random forest model predicting Mark 38 trades.

This model successfully identified:
- trades preceding major price movements.

Still, we remained cautious with ML throughout the competition.

<br/>

## Round 5

Round 5 completely changed the scale of the competition.

The jump to 50 assets massively expanded the research search space.

Initially, we built:
- giant correlation matrices,
- residual scanners,
- cointegration tests,
- lead-lag systems,
- imbalance signals,
- and family-wide relationship models.

At first, it looked like we found:
> unlimited alpha.

Everything seemed beautifully connected.

Residuals looked perfect.
Backtests exploded upward.
Entire families appeared predictable.

We became extremely skeptical.

### Out-of-Sample Collapse

We then performed proper out-of-sample testing:
- fit on two days,
- validate on the third.

The result was catastrophic.

Relationships immediately collapsed:
- hedge ratios inverted,
- residuals became non-stationary,
- correlations vanished,
- and most strategies disintegrated.

This was one of the most important lessons of the competition.

If you searched hard enough:
> you could absolutely find absurdly profitable backtests.

The hard part was finding relationships that survived reality.

### Final Strategy Philosophy

In the end:
- we discarded most cross-family complexity,
- kept only the most robust relationships,
- and prioritized simplicity heavily.

Ironically, several strategies we suspected were slightly overfit still ended up live because:
> at some point, you just have to decide and submit something.

<br/>

# Manual Challenge

## Round 1

The first manual round involved auction optimization.

The key realization:
> you pay the clearing price, not your bid.

This meant:
- bidding extremely high improved queue position,
- while not necessarily increasing cost.

We built a custom auction simulator and grid searched the optimal bids.

This ended up topping the leaderboard.

<br/>

## Round 2

Round 2 involved:
- research allocation,
- scale allocation,
- and speed allocation.

The interesting part:
- speed depended on what other teams selected.

We actually used:
- OpenAI,
- Anthropic,
- and repeated prompting

to estimate the likely distribution of participant allocations.

This surprisingly worked very well.

<br/>

## Round 3

Round 3 involved reserve-price optimization.

The difficult part was not optimization itself.

It was:
> estimating the average second bid submitted by all competitors.

We reused methods from previous manual rounds to estimate participant distributions and optimized accordingly.

<br/>

## Round 4

Round 4 manual introduced:
- spot trading,
- exotic derivatives,
- chooser options,
- binaries,
- knockouts,
- and CVaR optimization.

We built:
- Black-Scholes models for vanillas,
- Monte Carlo pricers for exotics,
- and CVaR optimization routines.

The biggest lesson:
> naive expected value optimization produced absurd tail risk.

We therefore optimized:
- conditional value-at-risk,
- rather than pure mean return.

<br/>

## Round 5

Round 5 manual was news trading.

The strongest idea here was comparing:
- previous years’ news,
- to current year assets,
- and mapping similar products across competitions.

The intuition:
- similar narratives likely produced similar magnitude moves.

We are still unsure how much edge this truly provided,
but it was one of the cleaner structural approaches available.

<br/>

# FAQ

## What mattered most?

Probably:
- structural understanding,
- skepticism,
- and avoiding overfitting.

Most strategies that looked magical initially ended up collapsing under proper testing.

The competition constantly rewarded:
- robustness,
- simplicity,
- and critical thinking.

<br/>

## Did machine learning matter?

Less than expected.

ML was useful mainly for:
- hypothesis generation,
- exploratory analysis,
- and occasionally filtering signals.

Most final production strategies were surprisingly simple.

<br/>

## Was preparation important?

Extremely.

A huge portion of our success came from:
- building infrastructure beforehand,
- studying previous writeups,
- understanding market microstructure,
- and creating fast research workflows.

Without that preparation, the round timers become overwhelming very quickly.

<br/>

# Conclusion

Throughout the competition, we tried to approach every product with the same philosophy:
- understand the generation process,
- test assumptions aggressively,
- avoid blind optimization,
- and prioritize robustness over elegance.

In our opinion, that mattered far more than any individual trick or model.

Prosperity is one of the rare competitions where:
- intuition,
- creativity,
- statistical thinking,
- engineering,
- and adaptability

all matter simultaneously.

That is also what makes it such a fantastic challenge.

We hope this writeup helps future participants:
- avoid some of our mistakes,
- develop stronger intuition,
- and continue pushing the competition forward.

Good luck next year :)

<br/>