import { renameSync, rmSync, writeFileSync } from 'node:fs';

/** Validate a complete bundle before atomically replacing the last known-good output. */
export async function writeValidatedGuideBundle(bundle, outputPath, validate) {
  await validate(bundle);
  const temporaryPath = `${outputPath}.${process.pid}.${Date.now()}.tmp`;
  try {
    writeFileSync(temporaryPath, `${JSON.stringify(bundle, null, 2)}\n`, 'utf8');
    renameSync(temporaryPath, outputPath);
  } finally {
    rmSync(temporaryPath, { force: true });
  }
}
