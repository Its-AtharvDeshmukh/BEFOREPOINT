# BEFOREPOINT Phase 4 design rationale

This is an original interface built inside the existing local project. The design research informed hierarchy and behavior; no proprietary screenshots or assets were copied into the product.

- [Apple Weather's current conditions and forecast interface](https://support.apple.com/guide/iphone/check-the-weather-iph1ac0b35f/ios): reviewed the actual phone screenshot. Our interpretation is to make the current state immediately legible and group supporting information in distinct cards. BEFOREPOINT puts the recommended response first on narrow screens, then its evidence and uncertainty. Weather remains a separately labeled external context card.
- [Apple Human Interface Guidelines](https://developer.apple.com/design/): used as a reference for restrained hierarchy, consistent controls and progressive disclosure. Detailed modeling workbenches remain available through disclosures rather than competing with the main decision.
- [Material foundations](https://m3.material.io/foundations/): shared palette, spacing, typography, interaction states and responsive arrangements. The app uses consistent panels, badges, inputs, focus indicators and failure states.
- [Linear's interface refresh](https://linear.app/now/behind-the-latest-design-refresh): reviewed the real before/after sidebar comparison. Our interpretation uses quiet navigation, consistent action placement and softer boundaries, keeping the working area prominent.
- [Stripe Apps design patterns](https://docs.stripe.com/stripe-apps/patterns): primary actions, request status, loading/empty/error states and clear table-based comparisons informed the experiment flow.

The dark system uses Inter with system fallback, cyan accents, semantic hypothesis colors, rounded panels and restrained transitions. Reduced-motion preferences are preserved. Light theme was not added in this phase: a partially converted theme would leave inconsistent contrast across the existing maps, graphs and charts.

Navigation stays at fourteen workspaces. PROVE ME WRONG contains ACT OR VERIFY; CASCADE CUT contains Domino Clock; INVISIBLE LIFELINES contains Silent Zone. Existing hash links continue to resolve to their new workspaces.

Command Center now includes the situation and response, four hypotheses, catalog-based next verification, source availability, next-failure forecasts, structural vulnerability, genuine weather context and map context. Full diagnostics remain expandable. The geographic grid encodes only one selected variable at a time. Graph comparison percentages are labeled baseline → selected plan; original edge assumptions stay visible.

Weather API extensions follow the [Open-Meteo provider contract](https://open-meteo.com/en/docs). Gusts, pressure, hourly visibility and two-day outlook are requested from the provider. Unavailable fields remain unavailable; historical averages are explicitly not connected.
