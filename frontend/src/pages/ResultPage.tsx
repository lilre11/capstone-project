import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { RankingResponse } from '../types';

const CRITERIA_LABELS: Record<string, string> = {
  price: 'Price',
  battery: 'Battery',
  camera_score: 'Camera',
  antutu: 'Performance',
  storage: 'Storage',
  weight: 'Weight',
  charging: 'Charging',
  screen_ratio: 'Screen',
};

interface Props {
  rankingData: RankingResponse | null;
}

export default function ResultPage({ rankingData }: Props) {
  const navigate = useNavigate();
  const [showDetails, setShowDetails] = useState(false);
  const [animatedScore, setAnimatedScore] = useState(0);
  const [animatedDash, setAnimatedDash] = useState(0);

  const top = rankingData?.top_match;
  const topEntry = rankingData?.rankings?.[0];
  const circumference = 2 * Math.PI * 58;

  // Animate score counter + ring draw
  useEffect(() => {
    if (!top) return;
    const target = top.score;
    const targetDash = circumference * (1 - target / 100);
    let current = 0;
    const step = target / 60;
    const timer = setInterval(() => {
      current += step;
      if (current >= target) {
        current = target;
        clearInterval(timer);
      }
      setAnimatedScore(current);
      setAnimatedDash(circumference * (1 - current / 100));
    }, 16);
    return () => clearInterval(timer);
  }, [top, circumference]);

  if (!rankingData || !top) {
    return (
      <div className="page-header">
        <h1>No Results Yet</h1>
        <p>Run an analysis first from the preferences page.</p>
        <Link to="/preferences" className="btn btn-primary mt-xl">
          Go to Preferences
        </Link>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      {/* Hero */}
      <div className="card result-hero">
        <div className="result-rank-badge">#{top.rank}</div>
        <div className="result-phone-name gradient-text">{top.model_name}</div>
        <div className="result-brand">{top.brand}</div>

        <div className="result-score-ring">
          <div className="score-circle">
            <svg width="140" height="140" viewBox="0 0 140 140">
              <circle cx="70" cy="70" r="58" fill="none" stroke="var(--surface-2)" strokeWidth="6" />
              <circle
                cx="70" cy="70" r="58" fill="none"
                stroke="var(--primary)" strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={animatedDash}
              />
            </svg>
            <div className="score-circle-value">
              <span className="score-number">{animatedScore.toFixed(1)}</span>
              <span className="score-label">/ 100</span>
            </div>
          </div>

          <div className="score-details">
            <div className="score-details-label">Closeness Coefficient</div>
            <div className="score-details-value">{top.closeness_coefficient.toFixed(4)}</div>
            <div className="score-details-method">Method: {rankingData.method}</div>
          </div>
        </div>
      </div>

      {/* Criteria cards */}
      {topEntry && (
        <div className="criteria-grid">
          {Object.entries(topEntry.weighted_normalized).map(([key, val]) => {
            const label = CRITERIA_LABELS[key] || key;
            const max = Math.max(...rankingData.rankings.map((r) => r.weighted_normalized[key] || 0));
            const pct = max > 0 ? (val / max) * 100 : 0;
            return (
              <motion.div
                key={key}
                className="card criteria-card"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <div className="criteria-card-header">
                  <span className="criteria-card-name">{label}</span>
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
          <span>TOPSIS Calculation Details</span>
          <span className={`toggle-arrow${showDetails ? ' open' : ''}`}>▼</span>
        </button>
        {showDetails && (
          <motion.div
            className="card-static topsis-content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
          >
            <h4 className="mb-md">Weights Used</h4>
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

            <h4 className="separation-title">Separation Distances (Top 5)</h4>
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
                    <td className="c-plus-value">{r.closeness_coefficient.toFixed(4)}</td>
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
          AI Explanation
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/compare')}>
          Compare Top 3
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/rankings')}>
          All Rankings
        </button>
        <button className="btn btn-ghost" onClick={() => navigate('/preferences')}>
          New Analysis
        </button>
      </div>
    </motion.div>
  );
}
