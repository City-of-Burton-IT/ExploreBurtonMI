// Reactive localStorage-backed values for the dismiss-once banner/modal
// pattern. All reads/writes are wrapped so blocked storage (private mode)
// degrades to session-only state instead of throwing.

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private mode -> persists for this session only */
  }
}

/** A one-way boolean flag ('1' when set), e.g. "this prompt was dismissed". */
export function persistedFlag(key: string) {
  let on = $state(read(key) === '1');
  return {
    get value() {
      return on;
    },
    set() {
      on = true;
      write(key, '1');
    },
  };
}

/** A persisted string, e.g. the signature of the last-dismissed banner content. */
export function persistedString(key: string) {
  let value = $state(read(key) ?? '');
  return {
    get value() {
      return value;
    },
    set(v: string) {
      value = v;
      write(key, v);
    },
  };
}

/** A persisted set of string ids (JSON array), e.g. per-alert dismissals. */
export function persistedStringSet(key: string) {
  const parse = (): Set<string> => {
    try {
      const raw = read(key);
      return new Set(raw ? (JSON.parse(raw) as string[]) : []);
    } catch {
      return new Set();
    }
  };
  let value = $state(parse());
  return {
    get value() {
      return value;
    },
    add(id: string) {
      value = new Set([...value, id]);
      write(key, JSON.stringify([...value]));
    },
  };
}
