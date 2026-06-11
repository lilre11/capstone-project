import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import type { RankingResponse } from '../types';

function rankBadgeClass(rank: number) {
  if (rank === 1) return 'rank-badge rank-gold';
  if (rank === 2) return 'rank-badge rank-silver';
  if (rank === 3) return 'rank-badge rank-bronze';
  return 'rank-badge rank-default';
}

interface Props {
  rankingData: RankingResponse | null;
}

export default function RankingsPage({ rankingData }: Props) {
  if (!rankingData) {
    return (
      <div className="page-header">
        <h1>No Rankings</h1>
        <p>Run an analysis first.</p>
        <Link to="/preferences" className="btn btn-primary mt-xl">Go to Preferences</Link>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <div className="page-header">
        <h1>Full <span className="gradient-text">Rankings</span></h1>
        <p>All 10 smartphones ranked by the TOPSIS closeness coefficient.</p>
      </div>

      <div className="card-static rankings-table-container">
        <table className="rankings-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Phone</th>
              <th>Brand</th>
              <th>C⁺ Score</th>
              <th className="score-bar-cell">Score / 100</th>
            </tr>
          </thead>
          <tbody>
            {rankingData.rankings.map((r, i) => (
              <motion.tr
                key={r.id}
                className="rankings-table-row"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <td>
                  <span className={rankBadgeClass(r.rank)}>
                    {r.rank}
                  </span>
                </td>
                <td className="text-sm" style={{ fontWeight: 600 }}>{r.model_name}</td>
                <td className="text-secondary text-sm">{r.brand}</td>
                <td className="font-mono text-secondary text-sm">
                  {r.closeness_coefficient.toFixed(4)}
                </td>
                <td className="score-bar-cell">
                  <div className="score-bar">
                    <div className="score-bar-track">
                      <div className="score-bar-fill" style={{ width: `${r.score}%` }} />
                    </div>
                    <span className="score-bar-value">{r.score.toFixed(1)}</span>
                  </div>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="action-row">
        <Link to="/results" className="btn btn-secondary">Back to Result</Link>
        <Link to="/compare" className="btn btn-secondary">Compare Top 3</Link>
        <Link to="/explain" className="btn btn-primary">AI Explanation</Link>
      </div>
    </motion.div>
  );
}
