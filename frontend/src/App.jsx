import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000/api/v1";

// ── Color system ──────────────────────────────────────────────────────────────
const REC_COLORS = {
  BUY: { bg: "#0a2e1a", border: "#00ff88", text: "#00ff88", label: "▲ BUY" },
  HOLD: { bg: "#2e2200", border: "#ffaa00", text: "#ffaa00", label: "◆ HOLD" },
  SELL: { bg: "#2e0a0a", border: "#ff4444", text: "#ff4444", label: "▼ SELL" },
  INSUFFICIENT_DATA: { bg: "#1a1a1a", border: "#666", text: "#666", label: "? N/A" },
};

const SEVERITY_COLORS = {
  LOW: "#ffaa00",
  MEDIUM: "#ff6b35",
  HIGH: "#ff4444",
};

// ── Inline styles ─────────────────────────────────────────────────────────────
const styles = {
  app: {
    minHeight: "100vh",
    background: "#080c10",
    color: "#e8edf2",
    fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
    padding: "0",
  },
  header: {
    borderBottom: "1px solid #1e2832",
    padding: "24px 40px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#0a0e14",
  },
  logo: {
    fontSize: "22px",
    fontWeight: "700",
    letterSpacing: "0.1em",
    color: "#00d4ff",
    fontFamily: "'IBM Plex Mono', monospace",
  },
  logoSub: {
    fontSize: "11px",
    color: "#4a6070",
    letterSpacing: "0.2em",
    marginTop: "2px",
  },
  statusDot: (ok) => ({
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    background: ok ? "#00ff88" : "#ff4444",
    display: "inline-block",
    marginRight: "8px",
    boxShadow: ok ? "0 0 6px #00ff88" : "0 0 6px #ff4444",
  }),
  main: {
    maxWidth: "1100px",
    margin: "0 auto",
    padding: "40px 40px",
  },
  searchSection: {
    marginBottom: "40px",
  },
  searchLabel: {
    fontSize: "11px",
    letterSpacing: "0.2em",
    color: "#4a6070",
    marginBottom: "12px",
    textTransform: "uppercase",
  },
  searchRow: {
    display: "flex",
    gap: "12px",
    alignItems: "center",
  },
  input: {
    background: "#0a0e14",
    border: "1px solid #1e2832",
    borderRadius: "4px",
    color: "#e8edf2",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "20px",
    fontWeight: "700",
    padding: "14px 20px",
    width: "200px",
    letterSpacing: "0.1em",
    outline: "none",
    textTransform: "uppercase",
    transition: "border-color 0.2s",
  },
  button: (loading) => ({
    background: loading ? "#0a2030" : "#00d4ff",
    border: "none",
    borderRadius: "4px",
    color: loading ? "#4a6070" : "#080c10",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "13px",
    fontWeight: "700",
    letterSpacing: "0.1em",
    padding: "14px 28px",
    cursor: loading ? "not-allowed" : "pointer",
    textTransform: "uppercase",
    transition: "all 0.2s",
  }),
  exampleTickers: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap",
    marginTop: "14px",
  },
  chip: {
    background: "#0a0e14",
    border: "1px solid #1e2832",
    borderRadius: "3px",
    color: "#4a8090",
    fontSize: "11px",
    fontFamily: "'IBM Plex Mono', monospace",
    padding: "5px 12px",
    cursor: "pointer",
    letterSpacing: "0.1em",
    transition: "all 0.15s",
  },
  loadingBox: {
    background: "#0a0e14",
    border: "1px solid #1e2832",
    borderRadius: "6px",
    padding: "40px",
    textAlign: "center",
  },
  loadingText: {
    color: "#00d4ff",
    fontSize: "13px",
    letterSpacing: "0.15em",
    marginBottom: "20px",
  },
  progressBar: {
    height: "2px",
    background: "#1e2832",
    borderRadius: "2px",
    overflow: "hidden",
    margin: "0 auto",
    width: "300px",
  },
  progressFill: {
    height: "100%",
    background: "linear-gradient(90deg, #00d4ff, #00ff88)",
    animation: "progress 2s ease-in-out infinite",
  },
  memoCard: {
    background: "#0a0e14",
    border: "1px solid #1e2832",
    borderRadius: "6px",
    overflow: "hidden",
  },
  memoHeader: (rec) => ({
    background: REC_COLORS[rec]?.bg || "#1a1a1a",
    borderBottom: `1px solid ${REC_COLORS[rec]?.border || "#333"}`,
    padding: "24px 32px",
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: "16px",
  }),
  memoTitle: {
    fontSize: "24px",
    fontWeight: "700",
    color: "#e8edf2",
    letterSpacing: "0.05em",
  },
  memoMeta: {
    fontSize: "12px",
    color: "#4a6070",
    marginTop: "4px",
    letterSpacing: "0.1em",
  },
  recBadge: (rec) => ({
    background: "transparent",
    border: `2px solid ${REC_COLORS[rec]?.border || "#666"}`,
    borderRadius: "4px",
    color: REC_COLORS[rec]?.text || "#666",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: "16px",
    fontWeight: "700",
    padding: "8px 20px",
    letterSpacing: "0.15em",
    whiteSpace: "nowrap",
  }),
  scoreRow: {
    display: "flex",
    gap: "24px",
    padding: "16px 32px",
    borderBottom: "1px solid #1e2832",
    background: "#080c10",
    flexWrap: "wrap",
  },
  scoreStat: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  scoreLabel: {
    fontSize: "10px",
    color: "#4a6070",
    letterSpacing: "0.2em",
    textTransform: "uppercase",
  },
  scoreValue: (color) => ({
    fontSize: "18px",
    fontWeight: "700",
    color: color || "#e8edf2",
    letterSpacing: "0.05em",
  }),
  memoBody: {
    padding: "32px",
  },
  section: {
    marginBottom: "28px",
  },
  sectionTitle: {
    fontSize: "10px",
    color: "#4a6070",
    letterSpacing: "0.25em",
    textTransform: "uppercase",
    marginBottom: "12px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  sectionLine: (color) => ({
    flex: 1,
    height: "1px",
    background: color || "#1e2832",
  }),
  summaryText: {
    fontSize: "14px",
    lineHeight: "1.7",
    color: "#b0bec8",
    letterSpacing: "0.02em",
  },
  grid2: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "20px",
  },
  caseBox: (color) => ({
    background: "#080c10",
    border: `1px solid ${color}22`,
    borderLeft: `3px solid ${color}`,
    borderRadius: "4px",
    padding: "16px 20px",
  }),
  caseTitle: (color) => ({
    fontSize: "10px",
    color: color,
    letterSpacing: "0.2em",
    textTransform: "uppercase",
    marginBottom: "10px",
    fontWeight: "700",
  }),
  caseItem: {
    fontSize: "13px",
    color: "#8fa0b0",
    marginBottom: "6px",
    lineHeight: "1.5",
    display: "flex",
    gap: "8px",
  },
  metricsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
    gap: "12px",
  },
  metricBox: {
    background: "#080c10",
    border: "1px solid #1e2832",
    borderRadius: "4px",
    padding: "12px 16px",
  },
  metricLabel: {
    fontSize: "10px",
    color: "#4a6070",
    letterSpacing: "0.15em",
    textTransform: "uppercase",
    marginBottom: "4px",
  },
  metricValue: {
    fontSize: "14px",
    color: "#00d4ff",
    fontWeight: "600",
    letterSpacing: "0.02em",
  },
  flagBox: {
    background: "#1a0e00",
    border: "1px solid #ff6b3533",
    borderRadius: "4px",
    padding: "12px 16px",
    marginBottom: "8px",
  },
  flagClaim: {
    fontSize: "13px",
    color: "#e8c090",
    marginBottom: "4px",
  },
  flagReason: {
    fontSize: "11px",
    color: "#8a6040",
    letterSpacing: "0.05em",
  },
  historySection: {
    marginTop: "48px",
  },
  historyTitle: {
    fontSize: "10px",
    color: "#4a6070",
    letterSpacing: "0.25em",
    textTransform: "uppercase",
    marginBottom: "16px",
  },
  historyGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
    gap: "12px",
  },
  historyCard: {
    background: "#0a0e14",
    border: "1px solid #1e2832",
    borderRadius: "4px",
    padding: "16px 20px",
    cursor: "pointer",
    transition: "border-color 0.2s",
  },
  historyTicker: {
    fontSize: "18px",
    fontWeight: "700",
    color: "#e8edf2",
    letterSpacing: "0.1em",
  },
  historyCompany: {
    fontSize: "11px",
    color: "#4a6070",
    marginTop: "2px",
    marginBottom: "10px",
    letterSpacing: "0.05em",
  },
  errorBox: {
    background: "#1a0505",
    border: "1px solid #ff4444",
    borderRadius: "4px",
    padding: "20px 24px",
    color: "#ff8888",
    fontSize: "13px",
    letterSpacing: "0.05em",
  },
};

// ── Components ────────────────────────────────────────────────────────────────

function ScoreBar({ score }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "#00ff88" : pct >= 60 ? "#ffaa00" : "#ff4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <div style={{ flex: 1, height: "4px", background: "#1e2832", borderRadius: "2px" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: "2px", transition: "width 1s ease" }} />
      </div>
      <span style={{ fontSize: "13px", color, fontWeight: "700", minWidth: "36px" }}>{pct}%</span>
    </div>
  );
}

function MemoView({ memo, onDownload }) {
  const rec = memo.recommendation || "INSUFFICIENT_DATA";
  const recColor = REC_COLORS[rec];

  const bulletPoints = (text) =>
    (text || "").split("|").map((p, i) => (
      <div key={i} style={styles.caseItem}>
        <span style={{ color: "#4a6070", flexShrink: 0 }}>—</span>
        <span>{p.trim()}</span>
      </div>
    ));

  const metrics = memo.metrics || {};
  const metricEntries = Object.entries(metrics).filter(([, v]) => v && v !== "null");

  return (
    <div style={styles.memoCard}>
      {/* Header */}
      <div style={styles.memoHeader(rec)}>
        <div>
          <div style={styles.memoTitle}>
            {memo.company_name} <span style={{ color: "#4a6070" }}>({memo.ticker})</span>
          </div>
          <div style={styles.memoMeta}>
            {new Date(memo.created_at).toLocaleString()} · Memo ID: {memo.memo_id?.slice(0, 8)}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "10px" }}>
          <div style={styles.recBadge(rec)}>{recColor?.label || rec}</div>
          <button
            onClick={onDownload}
            style={{ background: "transparent", border: "1px solid #1e2832", borderRadius: "3px", color: "#4a8090", fontFamily: "'IBM Plex Mono', monospace", fontSize: "11px", padding: "5px 14px", cursor: "pointer", letterSpacing: "0.1em" }}
          >
            ↓ PDF
          </button>
        </div>
      </div>

      {/* Score row */}
      <div style={styles.scoreRow}>
        <div style={styles.scoreStat}>
          <span style={styles.scoreLabel}>Confidence</span>
          <div style={{ width: "160px" }}><ScoreBar score={memo.confidence_score || 0} /></div>
        </div>
        <div style={styles.scoreStat}>
          <span style={styles.scoreLabel}>Flagged Claims</span>
          <span style={styles.scoreValue((memo.flagged_claims?.length || 0) > 0 ? "#ff6b35" : "#00ff88")}>
            {memo.flagged_claims?.length || 0}
          </span>
        </div>
        <div style={styles.scoreStat}>
          <span style={styles.scoreLabel}>Data Sources</span>
          <span style={styles.scoreValue("#e8edf2")}>
            {(memo.sources?.sec_filings?.length || 0) + (memo.sources?.news_articles?.length || 0)} sources
          </span>
        </div>
      </div>

      {/* Body */}
      <div style={styles.memoBody}>
        {/* Summary */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <span>Executive Summary</span>
            <div style={styles.sectionLine("#1e2832")} />
          </div>
          <div style={styles.summaryText}>
            {(memo.summary || "").split(" | ").map((p, i) => (
              <p key={i} style={{ margin: "0 0 8px 0" }}>{p}</p>
            ))}
          </div>
        </div>

        {/* Bull / Bear */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <span>Investment Thesis</span>
            <div style={styles.sectionLine("#1e2832")} />
          </div>
          <div style={styles.grid2}>
            <div style={styles.caseBox("#00ff88")}>
              <div style={styles.caseTitle("#00ff88")}>▲ Bull Case</div>
              {bulletPoints(memo.bull_case)}
            </div>
            <div style={styles.caseBox("#ff4444")}>
              <div style={styles.caseTitle("#ff4444")}>▼ Bear Case</div>
              {bulletPoints(memo.bear_case)}
            </div>
          </div>
        </div>

        {/* Metrics */}
        {metricEntries.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>
              <span>Key Metrics</span>
              <div style={styles.sectionLine("#1e2832")} />
            </div>
            <div style={styles.metricsGrid}>
              {metricEntries.map(([k, v]) => (
                <div key={k} style={styles.metricBox}>
                  <div style={styles.metricLabel}>{k.replace(/_/g, " ")}</div>
                  <div style={styles.metricValue}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Flagged Claims */}
        {memo.flagged_claims?.length > 0 && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>
              <span>⚠ Flagged Claims</span>
              <div style={styles.sectionLine("#ff6b35")} />
            </div>
            {memo.flagged_claims.map((f, i) => (
              <div key={i} style={styles.flagBox}>
                <div style={styles.flagClaim}>
                  <span style={{ color: SEVERITY_COLORS[f.severity] || "#ff6b35" }}>
                    [{f.severity}]
                  </span>{" "}
                  {f.claim}
                </div>
                <div style={styles.flagReason}>{f.reason}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState("");
  const [memo, setMemo] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  const [apiOk, setApiOk] = useState(null);

  const examples = ["AAPL", "MSFT", "NVDA", "GOOGL", "JPM", "TSLA"];

  // Check API health on mount
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => r.json())
      .then(d => setApiOk(d.status === "healthy"))
      .catch(() => setApiOk(false));

    // Load existing memos
    fetch(`${API_BASE}/memos`)
      .then(r => r.json())
      .then(setHistory)
      .catch(() => {});
  }, []);

  const analyze = async (t) => {
    const symbol = (t || ticker).toUpperCase().trim();
    if (!symbol) return;

    setLoading(true);
    setError(null);
    setMemo(null);
    setLoadingStep(`[1/3] Fetcher Agent — pulling SEC filings for ${symbol}...`);

    try {
      // Simulate step updates while waiting
      const steps = [
        `[1/3] Fetcher Agent — pulling SEC filings for ${symbol}...`,
        `[2/3] Analyst Agent — generating investment memo...`,
        `[3/3] Critic Agent — fact-checking and scoring...`,
      ];
      let step = 0;
      const stepInterval = setInterval(() => {
        step = (step + 1) % steps.length;
        setLoadingStep(steps[step]);
      }, 8000);

      const resp = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: symbol }),
      });

      clearInterval(stepInterval);

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Analysis failed");
      }

      const data = await resp.json();
      setMemo(data);

      // Refresh history
      fetch(`${API_BASE}/memos`)
        .then(r => r.json())
        .then(setHistory)
        .catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setLoadingStep("");
    }
  };

  const loadMemo = async (t) => {
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/memo/${t}`);
      if (!resp.ok) throw new Error("Memo not found");
      const data = await resp.json();
      setMemo(data);
      setTicker(t);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setError(e.message);
    }
  };

  const downloadPdf = async () => {
    if (!memo) return;
    window.open(`${API_BASE}/memo/${memo.ticker}/pdf`, "_blank");
  };

  return (
    <div style={styles.app}>
      {/* Inject Google Fonts + keyframes */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080c10; }
        input:focus { border-color: #00d4ff !important; }
        @keyframes progress {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
        .chip:hover { border-color: #00d4ff !important; color: #00d4ff !important; }
        .hist-card:hover { border-color: #2e3e50 !important; }
      `}</style>

      {/* Header */}
      <div style={styles.header}>
        <div>
          <div style={styles.logo}>FINSIGHT</div>
          <div style={styles.logoSub}>MULTI-AGENT FINANCIAL RESEARCH SYSTEM</div>
        </div>
        <div style={{ fontSize: "12px", color: "#4a6070", letterSpacing: "0.1em", display: "flex", alignItems: "center" }}>
          <span style={styles.statusDot(apiOk)} />
          {apiOk === null ? "CONNECTING..." : apiOk ? "API ONLINE" : "API OFFLINE"}
        </div>
      </div>

      {/* Main */}
      <div style={styles.main}>

        {/* Search */}
        <div style={styles.searchSection}>
          <div style={styles.searchLabel}>Enter ticker symbol to analyze</div>
          <div style={styles.searchRow}>
            <input
              style={styles.input}
              value={ticker}
              onChange={e => setTicker(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && analyze()}
              placeholder="AAPL"
              maxLength={10}
            />
            <button
              style={styles.button(loading)}
              onClick={() => analyze()}
              disabled={loading}
            >
              {loading ? "ANALYZING..." : "→ ANALYZE"}
            </button>
          </div>
          <div style={styles.exampleTickers}>
            {examples.map(t => (
              <button
                key={t}
                className="chip"
                style={styles.chip}
                onClick={() => { setTicker(t); analyze(t); }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div style={styles.loadingBox}>
            <div style={styles.loadingText}>{loadingStep}</div>
            <div style={styles.progressBar}>
              <div style={styles.progressFill} />
            </div>
            <div style={{ fontSize: "11px", color: "#2a3a4a", marginTop: "14px", letterSpacing: "0.15em" }}>
              SEC EDGAR + NEWS + LLM ANALYSIS · ~30s
            </div>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div style={styles.errorBox}>
            ❌ {error}
          </div>
        )}

        {/* Memo */}
        {memo && !loading && (
          <MemoView memo={memo} onDownload={downloadPdf} />
        )}

        {/* History */}
        {history.length > 0 && !loading && (
          <div style={styles.historySection}>
            <div style={styles.historyTitle}>Recent Analyses</div>
            <div style={styles.historyGrid}>
              {history.map(h => {
                const rec = h.recommendation || "INSUFFICIENT_DATA";
                const recColor = REC_COLORS[rec];
                return (
                  <div
                    key={h.memo_id}
                    className="hist-card"
                    style={styles.historyCard}
                    onClick={() => loadMemo(h.ticker)}
                  >
                    <div style={styles.historyTicker}>{h.ticker}</div>
                    <div style={styles.historyCompany}>{h.company_name || "—"}</div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "13px", color: recColor?.text || "#666", fontWeight: "700" }}>
                        {recColor?.label || rec}
                      </span>
                      <span style={{ fontSize: "11px", color: "#4a6070" }}>
                        {Math.round((h.confidence_score || 0) * 100)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}