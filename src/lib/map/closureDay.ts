import { localTodayISO } from '../closures';

type TimerHandle = ReturnType<typeof setTimeout>;

export interface LocalDayRolloverOptions {
  now?: () => Date;
  setTimer?: (callback: () => void, delay: number) => TimerHandle;
  clearTimer?: (handle: TimerHandle) => void;
}

/** Publishes the local calendar day and rearms at each following local midnight. */
export function startLocalDayRollover(
  onDayChange: (day: string) => void,
  options: LocalDayRolloverOptions = {},
): () => void {
  const now = options.now ?? (() => new Date());
  const setTimer = options.setTimer ?? ((callback, delay) => setTimeout(callback, delay));
  const clearTimer = options.clearTimer ?? ((handle) => clearTimeout(handle));
  let timer: TimerHandle | undefined;
  let stopped = false;

  function publishAndSchedule(): void {
    if (stopped) return;
    const current = now();
    onDayChange(localTodayISO(current));
    if (stopped) return;

    const nextMidnight = new Date(
      current.getFullYear(),
      current.getMonth(),
      current.getDate() + 1,
    );
    timer = setTimer(publishAndSchedule, nextMidnight.getTime() - current.getTime());
  }

  publishAndSchedule();

  return () => {
    if (stopped) return;
    stopped = true;
    if (timer !== undefined) clearTimer(timer);
    timer = undefined;
  };
}

