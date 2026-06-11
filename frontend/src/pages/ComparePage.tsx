import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
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

const BAR_COLORS = ['#06b6d4', '#22d3ee', '#0891b2'];

interface Props {
  rankingData: RankingResponse | null;
}

export default function ComparePage({ rankingData }: Props) {
  if (!rankingData || rankingData.rankings.length < 3) {
    return (
      <div className="page-header">
        <h1>No Data</h1>
        <p>Run an analysis first.</p>
        <Link to="/preferences" className="btn btn-primary mt-xl">Go to Preferences</Link>
      </div>
    );
  }

  const top3 = rankingData.rankings.slice(0, 3);
  const criteria = Object.keys(top3[0].weighted_normalized);

  const chartData = top3.map((r) => ({
    name: r.model_name.length > 14 ? r.model_name.slice(0, 14) + '…' : r.model_name,
    score: +r.score.toFixed(1),
  }));

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <div className="page-header">
        <h1>Compare <span className="gradient-text">Top 3</span></h1>
        <p>Side-by-side comparison of the highest ranked smartphones.</p>
      </div>

      {/* Cards */}
      <div className="compare-grid">
        {top3.map((r, i) => (
          <motion.div
            key={r.id}
            className={`card compare-card${i === 0 ? ' winner' : ''}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.15 }}
          >
            {i === 0 && <div className="compare-winner-badge">Best Match</div>}
            <div className="compare-rank gradient-text">#{r.rank}</div>
            <div className="compare-phone-name">{r.model_name}</div>
            <div className="compare-brand">{r.brand}</div>
            <div className="compare-score">{r.score.toFixed(1)}</div>
            <div className="compare-score-label">/ 100</div>
          </motion.div>
        ))}
      </div>

      {/* Criteria comparison */}
      <div className="card-static compare-criteria-wrapper">
        <table className="compare-criteria-table">
          <thead>
            <tr>
              <th>Criterion</th>
              {top3.map((r) => (
                <th key={r.id}>{r.model_name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {criteria.map((key) => {
              const vals = top3.map((r) => r.weighted_normalized[key] || 0);
              const maxVal = Math.max(...vals);
              return (
                <tr key={key}>
                  <td style={{ textAlign: 'left', fontWeight: 600 }}>
                    {CRITERIA_LABELS[key] || key}
                  </td>
                  {vals.map((v, i) => (
                    <td
                      key={top3[i].id}
                      className={v === maxVal && maxVal > 0 ? 'winner-cell' : ''}
                    >
                      {v.toFixed(4)}
                      {v === maxVal && maxVal > 0 && ' *'}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Bar chart */}
      <div className="card-static compare-chart-container">
        <h4 className="compare-chart-title">Overall Score Comparison</h4>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} barSize={50}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ background: '#1a1f2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f8fafc' }}
            />
            <Bar dataKey="score" radius={[6, 6, 0, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={BAR_COLORS[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="action-row">
        <Link to="/results" className="btn btn-secondary">Back to Result</Link>
        <Link to="/explain" className="btn btn-primary">AI Explanation</Link>
      </div>
    </motion.div>
  );
}
