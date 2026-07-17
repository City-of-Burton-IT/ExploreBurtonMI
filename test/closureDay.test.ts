import { describe, expect, it, vi } from 'vitest';
import { activeClosures, type RoadClosure } from '../src/lib/closures';
import { startLocalDayRollover } from '../src/lib/map/closureDay';

type TimerHandle = ReturnType<typeof setTimeout>;

function injectedClock(initial: Date) {
  let current = initial;
  let nextHandle = 1;
  const scheduled = new Map<TimerHandle, { callback: () => void; delay: number }>();

  const setTimer = vi.fn((callback: () => void, delay: number): TimerHandle => {
    const handle = nextHandle as unknown as TimerHandle;
    nextHandle += 1;
    scheduled.set(handle, { callback, delay });
    return handle;
  });
  const clearTimer = vi.fn((handle: TimerHandle) => {
    scheduled.delete(handle);
  });

  return {
    now: () => new Date(current),
    setCurrent(next: Date) {
      current = next;
    },
    setTimer,
    clearTimer,
    pendingDelay() {
      return [...scheduled.values()][0]?.delay;
    },
    pendingCount() {
      return scheduled.size;
    },
    fire() {
      const entry = [...scheduled.entries()][0];
      if (!entry) throw new Error('No timer is scheduled');
      scheduled.delete(entry[0]);
      entry[1].callback();
    },
  };
}

function closure(start: string, end: string): RoadClosure {
  return { road: 'Maple Rd', start, end };
}

describe('startLocalDayRollover', () => {
  it('moves unchanged records from active to empty at the next local midnight and cleans up', () => {
    const clock = injectedClock(new Date(2026, 5, 20, 23, 59, 30));
    const records = [closure('2026-06-20', '2026-06-20')];
    const projections: RoadClosure[][] = [];

    const stop = startLocalDayRollover(
      (day) => projections.push(activeClosures(records, day)),
      clock,
    );

    expect(projections).toEqual([records]);
    expect(clock.pendingDelay()).toBe(30_000);

    clock.setCurrent(new Date(2026, 5, 21, 0, 0, 0));
    clock.fire();

    expect(projections).toEqual([records, []]);
    expect(clock.pendingCount()).toBe(1);

    stop();
    expect(clock.clearTimer).toHaveBeenCalledTimes(1);
    expect(clock.pendingCount()).toBe(0);
  });

  it('moves unchanged records from empty to active and rearms for the following local midnight', () => {
    const clock = injectedClock(new Date(2026, 5, 19, 23, 59, 45));
    const records = [closure('2026-06-20', '2026-06-20')];
    const projections: RoadClosure[][] = [];

    const stop = startLocalDayRollover(
      (day) => projections.push(activeClosures(records, day)),
      clock,
    );

    expect(projections).toEqual([[]]);
    expect(clock.pendingDelay()).toBe(15_000);

    clock.setCurrent(new Date(2026, 5, 20, 0, 0, 0));
    clock.fire();

    expect(projections).toEqual([[], records]);
    expect(clock.pendingDelay()).toBe(24 * 60 * 60 * 1000);

    stop();
  });
});

