export interface MillageLevy {
  mills: number;
  voterApproved: boolean;
}

export function normaliseTaxableValue(value: number | null | undefined): number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0;
}

export function taxForMills(
  taxableValue: number | null | undefined,
  mills: number,
): number {
  return (normaliseTaxableValue(taxableValue) * mills) / 1_000;
}

export function sumLevyMills(
  levies: readonly MillageLevy[],
  voterApprovedOnly = false,
): number {
  return levies
    .filter((levy) => !voterApprovedOnly || levy.voterApproved)
    .reduce((sum, levy) => sum + levy.mills, 0);
}

export function roundedCents(value: number): number {
  const scaled = value * 100;
  return Math.round(scaled + Number.EPSILON * Math.abs(scaled));
}
