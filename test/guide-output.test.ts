import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { afterEach, describe, expect, it } from 'vitest';
import { writeValidatedGuideBundle } from '../tools/guide-output.mjs';

const directories: string[] = [];

afterEach(() => {
  for (const directory of directories.splice(0)) rmSync(directory, { recursive: true, force: true });
});

function outputFixture(): { directory: string; output: string } {
  const directory = mkdtempSync(join(tmpdir(), 'guide-output-'));
  directories.push(directory);
  return { directory, output: join(directory, 'guide.json') };
}

describe('guide bundle output', () => {
  it('preserves the last known-good file when validation fails', async () => {
    const { directory, output } = outputFixture();
    writeFileSync(output, 'last known good\n', 'utf8');

    await expect(
      writeValidatedGuideBundle({ invalid: true }, output, () => {
        throw new Error('invalid bundle');
      }),
    ).rejects.toThrow('invalid bundle');

    expect(readFileSync(output, 'utf8')).toBe('last known good\n');
    expect(readdirSync(directory)).toEqual(['guide.json']);
  });

  it('writes the validated bundle with a trailing newline', async () => {
    const { output } = outputFixture();
    const bundle = { sections: [], content: {} };
    await writeValidatedGuideBundle(bundle, output, () => bundle);
    expect(readFileSync(output, 'utf8')).toBe(`${JSON.stringify(bundle, null, 2)}\n`);
  });
});
