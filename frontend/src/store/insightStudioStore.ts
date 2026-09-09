import { create } from 'zustand';
import * as api from '../services/dataScience';
import type { DatasetOverview } from '../types/dataScience';

// A dataset handed off from another surface (e.g. the "Analyze Dataset" action
// on a chat query result) that Insight Studio should turn into a session.
export interface PendingDataset {
  columns: string[];
  rows: Record<string, unknown>[];
  name?: string;
  source?: string;
  source_detail?: Record<string, unknown>;
}

interface InsightStudioState {
  pending: PendingDataset | null;
  sessionId: string | null;
  dataset: DatasetOverview | null;
  loading: boolean;
  error: string | null;

  setPending: (dataset: PendingDataset) => void;
  clearPending: () => void;
  createFromPending: () => Promise<string | null>;
  startDemo: () => Promise<string | null>;
  loadSession: (sessionId: string) => Promise<void>;
  refreshOverview: () => Promise<void>;
  reset: () => void;
}

function message(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

// Persist the handoff so it survives a full navigation to /insight-studio
// (the chat "Analyze Dataset" control is a plain link, so the store is recreated).
const PENDING_KEY = 'insightstudio:pending';

function readPending(): PendingDataset | null {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY);
    return raw ? (JSON.parse(raw) as PendingDataset) : null;
  } catch {
    return null;
  }
}

function writePending(dataset: PendingDataset | null): void {
  try {
    if (dataset) sessionStorage.setItem(PENDING_KEY, JSON.stringify(dataset));
    else sessionStorage.removeItem(PENDING_KEY);
  } catch {
    /* storage unavailable — non-fatal */
  }
}

export const useInsightStudioStore = create<InsightStudioState>((set, get) => ({
  pending: readPending(),
  sessionId: null,
  dataset: null,
  loading: false,
  error: null,

  setPending: (dataset) => {
    writePending(dataset);
    set({ pending: dataset });
  },
  clearPending: () => {
    writePending(null);
    set({ pending: null });
  },

  createFromPending: async () => {
    const pending = get().pending;
    if (!pending) return get().sessionId;
    set({ loading: true, error: null });
    try {
      const res = await api.createSession(pending);
      writePending(null);
      set({ sessionId: res.session_id, dataset: res.dataset, pending: null, loading: false });
      return res.session_id;
    } catch (err) {
      set({ loading: false, error: message(err, 'Failed to create analysis session') });
      return null;
    }
  },

  startDemo: async () => {
    set({ loading: true, error: null });
    try {
      const res = await api.createDemoSession();
      set({ sessionId: res.session_id, dataset: res.dataset, pending: null, loading: false });
      return res.session_id;
    } catch (err) {
      set({ loading: false, error: message(err, 'Failed to start the demo dataset') });
      return null;
    }
  },

  loadSession: async (sessionId) => {
    set({ loading: true, error: null });
    try {
      const dataset = await api.getSession(sessionId);
      set({ sessionId, dataset, loading: false });
    } catch (err) {
      set({ loading: false, error: message(err, 'That analysis session could not be loaded') });
    }
  },

  refreshOverview: async () => {
    const sessionId = get().sessionId;
    if (!sessionId) return;
    try {
      const dataset = await api.getSession(sessionId);
      set({ dataset });
    } catch {
      /* non-fatal */
    }
  },

  reset: () => {
    writePending(null);
    set({ pending: null, sessionId: null, dataset: null, error: null, loading: false });
  },
}));
