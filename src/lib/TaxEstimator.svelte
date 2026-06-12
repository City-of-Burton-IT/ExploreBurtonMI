<script lang="ts">
  import type { InfoEstimator } from './types';

  let { data }: { data: InfoEstimator } = $props();

  // Inputs. Default to a typical Burton home and the first district.
  let taxableValue = $state(50000);
  let districtIdx = $state(0);
  let homestead = $state(true);

  const district = $derived(data.districts[districtIdx] ?? data.districts[0]);
  const totalRate = $derived(homestead ? district.homestead : district.nonHomestead);

  const dollars = (mills: number) => Math.round((mills * taxableValue) / 1000);
  const cityAmt = $derived(dollars(data.cityMills));
  const countyAmt = $derived(dollars(data.countyMills));
  const totalAmt = $derived(dollars(totalRate));
  const restAmt = $derived(Math.max(0, totalAmt - cityAmt - countyAmt));
  const cityPct = $derived(totalAmt ? Math.round((cityAmt / totalAmt) * 100) : 0);

  const fmt = (n: number) => n.toLocaleString('en-US');
</script>

<div class="estimator">
  <h3>Estimate your tax bill</h3>
  <p class="lead">
    See roughly how a property tax bill splits. Enter your home's <strong>taxable value</strong>
    (about half its market value, shown on your assessment notice).
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

  <div class="result">
    <div class="total">
      <span class="amt">${fmt(totalAmt)}<span class="per">/yr</span></span>
      <span class="cap">estimated total property tax</span>
    </div>
    <ul class="split">
      <li><span class="dot" style="background:#2c57a0"></span> City of Burton <b>${fmt(cityAmt)}</b></li>
      <li><span class="dot" style="background:#c0392b"></span> Genesee County <b>${fmt(countyAmt)}</b></li>
      <li><span class="dot" style="background:#e08a00"></span> Schools &amp; other <b>${fmt(restAmt)}</b></li>
    </ul>
    <p class="takeaway">
      Only about <strong>{cityPct}%</strong> of this bill (${fmt(cityAmt)}) goes to the City of Burton.
    </p>
  </div>
  <p class="fineprint">
    Estimate only, at {totalRate.toFixed(2)} mills for {district.name}
    ({homestead ? 'homestead' : 'non-homestead'}). Your actual bill depends on exact taxable value,
    special assessments, and any exemptions. Not a tax statement.
  </p>
</div>

<style>
  .estimator {
    background: var(--civic-blue-tint, #eef3fb);
    border: 1px solid #d6e0f0;
    border-radius: var(--pub-radius, 10px);
    padding: 1rem 1.1rem 1.1rem;
    margin: 0 0 1.6rem;
  }
  h3 {
    margin: 0 0 0.3rem;
    font-family: var(--font-head, sans-serif);
    font-weight: 700;
    font-size: 1.1rem;
    color: var(--civic-blue, #2c57a0);
  }
  .lead {
    margin: 0 0 0.9rem;
    font-size: 0.9rem;
    color: #444;
  }
  .controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.7rem 1rem;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--pub-ink);
  }
  input,
  select {
    font-size: 0.95rem;
    padding: 0.45rem 0.55rem;
    border: 1px solid #b9c6db;
    border-radius: var(--pub-radius-sm, 6px);
    background: var(--pub-surface);
    font-family: inherit;
  }
  .inputwrap {
    position: relative;
    display: flex;
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
    padding-left: 1.3rem;
    width: 100%;
    box-sizing: border-box;
  }
  .result {
    margin-top: 1rem;
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.6rem 1.4rem;
    align-items: center;
  }
  .total {
    display: flex;
    flex-direction: column;
    padding: 0.6rem 1rem 0.6rem 0;
    border-right: 1px solid #cdd8ea;
  }
  .amt {
    font-family: var(--font-head, sans-serif);
    font-weight: 800;
    font-size: 1.7rem;
    color: var(--civic-blue, #2c57a0);
    line-height: 1;
  }
  .per {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--pub-muted);
  }
  .cap {
    font-size: 0.78rem;
    color: var(--pub-muted);
    margin-top: 0.2rem;
  }
  .split {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.9rem;
    color: var(--pub-ink);
  }
  .split b {
    color: var(--pub-ink);
  }
  .dot {
    display: inline-block;
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    margin-right: 0.4rem;
    vertical-align: middle;
  }
  .takeaway {
    grid-column: 1 / -1;
    margin: 0.4rem 0 0;
    font-size: 0.9rem;
    color: var(--pub-ink);
  }
  .fineprint {
    margin: 0.8rem 0 0;
    font-size: 0.72rem;
    line-height: 1.4;
    color: var(--pub-muted, #5c5c5c);
  }
  @media (max-width: 520px) {
    .result {
      grid-template-columns: 1fr;
    }
    .total {
      border-right: none;
      border-bottom: 1px solid #cdd8ea;
      padding: 0 0 0.6rem;
    }
  }
</style>
