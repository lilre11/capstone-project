import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { RankingResponse } from '../types';

const CRITERIA_LABELS: Record<string, { label: string; icon: string }> = {
  price: { label: 'Price', icon: '💰' },
  battery: { label: 'Battery', icon: '🔋' },
  camera_score: { label: 'Camera', icon: '📸' },
  antutu: { label: 'Performance', icon: '⚡' },
  storage: { label: 'Storage', icon: '💾' },
  weight: { label: 'Weight', icon: '🪶' },
  charging: { label: 'Charging', icon: '🔌' },
  screen_ratio: { label: 'Screen', icon: '📱' },
};

interface Props {
  rankingData: RankingResponse | null;
}

export default function ResultPage({ rankingData }: Props) {
  const navigate = useNavigate();
  const [showDetails, setShowDetails] = useState(false);
  const [animatedScore, setAnimatedScore] = useState(0);

  const top = rankingData?.top_match;
  const topEntry = rankingData?.rankings?.[0];

  // Animate score counter
  useEffect(() => {
    if (!top) return;
    const target = top.score;
    let current = 0;
    const step = target / 60;
    const timer = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      setAnimatedScore(current);
    }, 16);
    return () => clearInterval(timer);
  }, [top]);

  if (!rankingData || !top) {
    return (
      <div className="page-header">
        <h1>No Results Yet</h1>
        <p>Run an analysis first from the preferences page.</p>
        <Link to="/preferences" className="btn btn-primary" style={{ marginTop: 24 }}>
          Go to Preferences
        </Link>
      </div>
    );
  }

  const circumference = 2 * Math.PI * 65;
  const scorePercent = top.score / 100;
  const dashOffset = circumference * (1 - scorePercent);

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      {/* Hero */}
      <div className="glass-card result-hero">
        <div className="result-rank-badge">#{top.rank}</div>
        <div className="result-phone-name gradient-text">{top.model_name}</div>
        <div className="result-brand">{top.brand}</div>

        <div className="result-score-ring">
          <div className="score-circle">
            <svg width="160" height="160">
              <circle cx="80" cy="80" r="65" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
              <circle
                cx="80" cy="80" r="65" fill="none"
                stroke="url(#scoreGrad)" strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                style={{ transition: 'stroke-dashoffset 1.5s ease-out' }}
              />
              <defs>
                <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#3b82f6" />
                  <stop offset="100%" stopColor="#8b5cf6" />
                </linearGradient>
              </defs>
            </svg>
            <div className="score-circle-value">
              <span className="score-number">{animatedScore.toFixed(1)}</span>
              <span className="score-label">/ 100</span>
            </div>
          </div>

          <div style={{ textAlign: 'left' }}>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', marginBottom: 4 }}>
              Closeness Coefficient
            </div>
            <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 700 }}>
              {top.closeness_coefficient.toFixed(4)}
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 8 }}>
              Method: {rankingData.method}
            </div>
          </div>
        </div>
      </div>

      {/* Criteria cards */}
      {topEntry && (
        <div className="criteria-grid">
          {Object.entries(topEntry.weighted_normalized).map(([key, val]) => {
            const meta = CRITERIA_LABELS[key] || { label: key, icon: '📊' };
            const max = Math.max(...rankingData.rankings.map((r) => r.weighted_normalized[key] || 0));
            const pct = max > 0 ? (val / max) * 100 : 0;
            return (
              <motion.div
                key={key}
                className="glass-card criteria-card"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="criteria-card-header">
                  <span className="criteria-card-name">{meta.icon} {meta.label}</span>
                  <span className="criteria-card-value">{val.toFixed(4)}</span>
                </div>
                <div className="criteria-bar">
                  <div className="criteria-bar-fill" style={{ width: `${pct}%` }} />
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* TOPSIS Details */}
      <div className="topsis-panel">
        <button className="topsis-toggle" onClick={() => setShowDetails(!showDetails)}>
          <span>📐 TOPSIS Calculation Details</span>
          <span className={`toggle-arrow${showDetails ? ' open' : ''}`}>▼</span>
        </button>
        {showDetails && (
          <motion.div
            className="glass-card-static topsis-content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
          >
            <h4 style={{ marginBottom: 12 }}>Weights Used</h4>
            <table className="topsis-table">
              <thead>
                <tr>
                  <th>Criterion</th>
                  <th>Weight</th>
                  <th>Direction</th>
                  <th>Ideal Best (A⁺)</th>
                  <th>Ideal Worst (A⁻)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(rankingData.weights_used).map(([k, w]) => (
                  <tr key={k}>
                    <td>{CRITERIA_LABELS[k]?.label || k}</td>
                    <td>{w.toFixed(4)}</td>
                    <td>{rankingData.criteria_directions[k]}</td>
                    <td>{rankingData.ideal_best[k]?.toFixed(4)}</td>
                    <td>{rankingData.ideal_worst[k]?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h4 style={{ margin: '20px 0 12px' }}>Separation Distances (Top 5)</h4>
            <table className="topsis-table">
              <thead>
                <tr><th>Rank</th><th>Phone</th><th>S⁺</th><th>S⁻</th><th>C⁺</th></tr>
              </thead>
              <tbody>
                {rankingData.rankings.slice(0, 5).map((r) => (
                  <tr key={r.id}>
                    <td>#{r.rank}</td>
                    <td>{r.model_name}</td>
                    <td>{r.s_plus.toFixed(4)}</td>
                    <td>{r.s_minus.toFixed(4)}</td>
                    <td style={{ color: 'var(--accent-blue)', fontWeight: 700 }}>{r.closeness_coefficient.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </motion.div>
        )}
      </div>

      {/* Actions */}
      <div className="result-actions">
        <button className="btn btn-primary" onClick={() => navigate('/explain')}>
          🤖 AI Explanation
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/compare')}>
          📊 Compare Top 3
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/rankings')}>
          📋 All Rankings
        </button>
        <button className="btn btn-ghost" onClick={() => navigate('/preferences')}>
          ← New Analysis
        </button>
      </div>
    </motion.div>
  );
}
