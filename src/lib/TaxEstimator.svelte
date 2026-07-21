<script lang="ts">
  import type { InfoEstimator } from './types';
  import {
    normaliseTaxableValue,
    roundedCents,
    sumLevyMills,
    taxForMills,
  } from './propertyTax';

  let { data }: { data: InfoEstimator } = $props();

  let taxableValue = $state<number | undefined>(50_000);
  let districtIdx = $state(0);
  let homestead = $state(true);

  const district = $derived(data.districts[districtIdx] ?? data.districts[0]);
  const safeTaxableValue = $derived(normaliseTaxableValue(taxableValue));
  const totalRate = $derived(homestead ? district.homestead : district.nonHomestead);
  const cityRows = $derived(
    data.cityLevies.map((levy) => ({
      ...levy,
      amount: taxForMills(safeTaxableValue, levy.mills),
    })),
  );
  const cityTotal = $derived(taxForMills(safeTaxableValue, data.cityMills));
  const voterMills = $derived(sumLevyMills(data.cityLevies, true));
  const voterTotal = $derived(taxForMills(safeTaxableValue, voterMills));
  const completeBillTotal = $derived(taxForMills(safeTaxableValue, totalRate));
  const rowCents = $derived(
    cityRows.reduce((sum, row) => sum + roundedCents(row.amount), 0),
  );
  const totalCents = $derived(roundedCents(cityTotal));
  const hasRoundingDifference = $derived(rowCents !== totalCents);

  const currency = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const fmtCurrency = (value: number) => currency.format(roundedCents(value) / 100);
  const fmtMills = (value: number) => value.toFixed(4);
</script>

<div class="estimator">
  <h3>Estimate your tax bill</h3>
  <p class="lead">
    Enter the <strong>taxable value</strong> from your assessment notice. The first result shows
    exactly how the adopted City levy supports City services; the second estimates your complete bill.
  </p>

  <div class="controls">
    <label>
      Taxable value
      <span class="inputwrap">
        <span class="prefix">$</span>
        <input type="number" min="0" step="1000" bind:value={taxableValue} />
      </span>
    </label>
    <label>
      School district
      <select bind:value={districtIdx}>
        {#each data.districts as d, i (d.name)}
          <option value={i}>{d.name}</option>
        {/each}
      </select>
    </label>
    <label>
      Property type
      <select bind:value={homestead}>
        <option value={true}>Homestead (I live here)</option>
        <option value={false}>Non-homestead (rental / 2nd home)</option>
      </select>
    </label>
  </div>

  <section class="city-result" aria-labelledby="city-tax-heading">
    <div class="result-heading">
      <div>
        <h4 id="city-tax-heading">Your City of Burton taxes</h4>
        <p>{data.cityRatePeriod}</p>
      </div>
      <div class="result-total">
        <strong>{fmtCurrency(cityTotal)}</strong>
        <span>estimated City total per year</span>
      </div>
    </div>

    <table>
      <caption class="sr-only">City of Burton millage and estimated annual tax by service</caption>
      <colgroup>
        <col class="service-col" />
        <col class="authorization-col" />
        <col class="mills-col" />
        <col class="amount-col" />
      </colgroup>
      <thead>
        <tr>
          <th scope="col">City service</th>
          <th scope="col">Who authorized it</th>
          <th scope="col">Mills</th>
          <th scope="col">Your annual amount</th>
        </tr>
      </thead>
      <tbody>
        {#each cityRows as levy (levy.id)}
          <tr>
            <th scope="row">
              {levy.service}
              <span class="description">{levy.description}</span>
            </th>
            <td><span class="authorization">{levy.authorization}</span></td>
            <td class="numeric">{fmtMills(levy.mills)}</td>
            <td class="numeric amount">{fmtCurrency(levy.amount)}</td>
          </tr>
        {/each}
      </tbody>
      <tfoot>
        <tr>
          <th scope="row" colspan="2">City of Burton total</th>
          <td class="numeric">{fmtMills(data.cityMills)}</td>
          <td class="numeric amount">{fmtCurrency(cityTotal)}</td>
        </tr>
      </tfoot>
    </table>

    {#if hasRoundingDifference}
      <p class="rounding-note">
        Individually rounded service amounts can differ from the combined City total by one cent.
      </p>
    {/if}

    <p class="voter-takeaway">
      Police and Fire account for <strong>{fmtMills(voterMills)} voter-approved mills</strong>,
      or <strong>{fmtCurrency(voterTotal)}</strong> of this City estimate.
    </p>
  </section>

  <section class="complete-result" aria-labelledby="complete-tax-heading">
    <div>
      <h4 id="complete-tax-heading">Estimated complete property-tax bill</h4>
      <p>
        {data.fullBillRatePeriod} for {district.name}
        ({homestead ? 'homestead' : 'non-homestead'})
      </p>
    </div>
    <div class="complete-total">
      <strong>{fmtCurrency(completeBillTotal)}</strong>
      <span>{totalRate.toFixed(2)} mills per year</span>
    </div>
    <p>
      This complete-bill estimate includes County, schools, the State, ISD, college,
      transit, airport, and other authorities. Those amounts do not become City of Burton revenue.
    </p>
  </section>

  <p class="fineprint">
    Estimate only. Actual bills can differ because of exact parcel values, exemptions, special
    assessments, administrative fees, and a possible Downtown Development Authority levy for
    affected parcels. Not a tax statement.
  </p>
</div>

<style>
  .estimator {
    min-width: 0;
    margin: 0 0 1.6rem;
    padding: 1rem;
    border: 1px solid var(--pub-border);
    border-radius: var(--pub-radius, 10px);
    background: var(--pub-surface-2);
    color: var(--pub-ink);
  }
  h3,
  h4 {
    margin: 0;
    color: var(--civic-blue-link);
    font-family: var(--font-head, sans-serif);
  }
  h3 {
    font-size: 1.1rem;
  }
  h4 {
    font-size: 1rem;
  }
  .lead,
  .result-heading p,
  .complete-result > div:first-child p,
  .description,
  .rounding-note,
  .fineprint {
    color: var(--pub-muted);
  }
  .lead {
    margin: 0.3rem 0 0.9rem;
    font-size: 0.9rem;
  }
  .controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.7rem 1rem;
    min-width: 0;
  }
  label {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.25rem;
    color: var(--pub-ink);
    font-size: 0.8rem;
    font-weight: 600;
  }
  input,
  select {
    box-sizing: border-box;
    max-width: 100%;
    padding: 0.45rem 0.55rem;
    border: 1px solid var(--pub-border);
    border-radius: var(--pub-radius-sm, 6px);
    background: var(--pub-surface);
    color: var(--pub-ink);
    font-family: inherit;
    font-size: 0.95rem;
  }
  .inputwrap {
    position: relative;
    display: flex;
    min-width: 0;
    align-items: center;
  }
  .prefix {
    position: absolute;
    left: 0.55rem;
    color: var(--pub-muted);
    font-size: 0.95rem;
    pointer-events: none;
  }
  .inputwrap input {
    width: 100%;
    padding-left: 1.3rem;
  }
  .city-result,
  .complete-result {
    min-width: 0;
    margin-top: 1rem;
    padding: 0.9rem;
    border: 1px solid var(--pub-border);
    border-radius: var(--pub-radius-sm, 8px);
    background: var(--pub-surface);
  }
  .result-heading,
  .complete-result {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.75rem 1rem;
    align-items: start;
  }
  .result-heading p,
  .complete-result > div:first-child p {
    margin: 0.15rem 0 0;
    font-size: 0.78rem;
  }
  .result-total,
  .complete-total {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    text-align: right;
  }
  .result-total strong,
  .complete-total strong,
  .amount {
    color: var(--civic-blue-link);
    font-weight: 800;
  }
  .result-total strong,
  .complete-total strong {
    font-size: 1.35rem;
  }
  .result-total span,
  .complete-total span {
    color: var(--pub-muted);
    font-size: 0.72rem;
  }
  table {
    width: 100%;
    margin-top: 0.8rem;
    border-collapse: collapse;
    table-layout: fixed;
  }
  .service-col {
    width: 31%;
  }
  .authorization-col {
    width: 25%;
  }
  .mills-col {
    width: 18%;
  }
  .amount-col {
    width: 26%;
  }
  th,
  td {
    padding: 0.55rem 0.45rem;
    border-bottom: 1px solid var(--pub-border);
    color: var(--pub-ink);
    text-align: left;
    vertical-align: top;
    overflow-wrap: anywhere;
  }
  thead th {
    color: var(--pub-muted);
    font-size: 0.75rem;
  }
  tbody th,
  tfoot th {
    font-weight: 700;
  }
  .description {
    display: block;
    margin-top: 0.15rem;
    font-size: 0.72rem;
    font-weight: 400;
    line-height: 1.35;
  }
  .authorization {
    font-weight: 600;
  }
  .numeric {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  tfoot th,
  tfoot td {
    border-top: 2px solid var(--pub-border);
    border-bottom: 0;
  }
  .voter-takeaway,
  .complete-result > p {
    grid-column: 1 / -1;
    margin: 0.75rem 0 0;
    color: var(--pub-ink);
  }
  .voter-takeaway {
    font-size: 0.9rem;
  }
  .complete-result > p {
    font-size: 0.82rem;
    line-height: 1.45;
  }
  .rounding-note {
    margin: 0.5rem 0 0;
    font-size: 0.72rem;
  }
  .fineprint {
    margin: 0.8rem 0 0;
    font-size: 0.72rem;
    line-height: 1.4;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  @media (max-width: 520px) {
    .estimator,
    .city-result,
    .complete-result {
      padding: 0.75rem;
    }
    .controls {
      grid-template-columns: 1fr;
    }
    .result-heading,
    .complete-result {
      grid-template-columns: 1fr;
    }
    .result-total,
    .complete-total {
      align-items: flex-start;
      text-align: left;
    }
    .service-col {
      width: 29%;
    }
    .authorization-col {
      width: 24%;
    }
    .mills-col {
      width: 20%;
    }
    .amount-col {
      width: 27%;
    }
    th,
    td {
      padding: 0.45rem 0.25rem;
      font-size: 0.72rem;
    }
    .description {
      display: none;
    }
  }
</style>
