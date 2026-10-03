# Random-wire length estimates

![Coloured wire-length chart](random-wire-core.png)

Display: **0–135 ft** (0–41.15 m). Padding around half-wave intervals: **0 ft**.

## Bands

| Band | UK range (MHz) | Priority |
|---|---|---|
| 40 m | 7.000–7.200 | Main |
| 30 m | 10.100–10.150 | Main |
| 20 m | 14.000–14.350 | Main |

Frequency limits: [Ofcom OFW611, Tables B/C](https://www.ofcom.org.uk/siteassets/resources/documents/spectrum/emf/emf-amateur-licence-terms-and-conditions.pdf?v=386197), checked 3 October 2026.

## Reading the chart

Each band has its own colour and row. The combined rows merge its half-wave intervals; the main-band row only combines selected 40, 30 and 20 m bands. Grey hatching shows the original model's quarter-wave minimum-length guide, derived separately from the lowest frequency in each row. This is a guide, not a hard tuning limit.

For all selected bands, that guide is **33.429 ft** (10.189 m).

The calculation uses the original `468 / frequency_MHz` estimate and includes every integer multiple intersecting the display, without the old six-multiple cap. Intervals crossing the right edge are clipped. Labels such as `3×` mean three half-waves.

For an end-fed random wire, these intervals can present high impedances that some tuners cannot match. [Original author's explanation](https://copland.udel.edu/~mm/ham/randomWire/indexOld.html). A deliberate end-fed half-wave with a suitable matching network is a different setup.

## Unflagged spans for all selected bands

These are gaps in this estimate, above the quarter-wave guide. Endpoints touch flagged intervals, so they should not be treated as recommended cut lengths. Installation, wire insulation, counterpoise and matching equipment affect actual behaviour. Optional padding shrinks these spans but does not model those effects.

| Feet | Metres |
|---|---|
| 33.429–46.108 | 10.189–14.054 |
| 46.337–65.000 | 14.123–19.812 |
| 66.857–92.217 | 20.378–28.108 |
| 92.673–97.840 | 28.247–29.822 |
| 100.286–130.000 | 30.567–39.624 |
| 133.714–135.000 | 40.756–41.148 |

## Half-wave intervals

Values below exclude optional padding. A † marks an interval clipped at the display limit.

| Band | Multiple | Feet | Metres |
|---|---|---|---|
| 40 m | 1× | 65.000–66.857 | 19.812–20.378 |
| 40 m | 2× | 130.000–133.714 | 39.624–40.756 |
| 30 m | 1× | 46.108–46.337 | 14.054–14.123 |
| 30 m | 2× | 92.217–92.673 | 28.108–28.247 |
| 20 m | 1× | 32.613–33.429 | 9.941–10.189 |
| 20 m | 2× | 65.226–66.857 | 19.881–20.378 |
| 20 m | 3× | 97.840–100.286 | 29.822–30.567 |
| 20 m | 4× | 130.453–133.714 | 39.762–40.756 |

[Full-precision calculation data](random-wire-core.json)
