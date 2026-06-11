import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { submitPreferences, runRanking } from '../api/client';
import type { PreferencesRequest, RankingResponse } from '../types';

type PreferenceKey = keyof PreferencesRequest;

const CRITERIA = [
  { key: 'price', label: 'Price Sensitivity', icon: '💰', desc: 'How important is a lower price?' },
  { key: 'battery', label: 'Battery Life', icon: '🔋', desc: 'Long-lasting battery matters?' },
  { key: 'camera', label: 'Camera Quality', icon: '📸', desc: 'Photo and video performance' },
  { key: 'antutu', label: 'Performance', icon: '⚡', desc: 'Raw processing power (AnTuTu)' },
  { key: 'storage', label: 'Storage Capacity', icon: '💾', desc: 'How much storage do you need?' },
  { key: 'weight', label: 'Lightweight', icon: '🪶', desc: 'Prefer a lighter phone?' },
  { key: 'charging', label: 'Charging Speed', icon: '🔌', desc: 'Fast charging capability' },
  { key: 'screen_ratio', label: 'Screen Size', icon: '📱', desc: 'Edge-to-edge display ratio' },
] satisfies Array<{ key: PreferenceKey; label: string; icon: string; desc: string }>;

const PRESETS: Record<string, Record<string, number>> = {
  balanced: { price: 50, battery: 50, camera: 50, antutu: 50, storage: 50, weight: 50, charging: 50, screen_ratio: 50 },
  camera_lover: { price: 30, battery: 40, camera: 100, antutu: 40, storage: 60, weight: 30, charging: 30, screen_ratio: 60 },
  budget: { price: 100, battery: 60, camera: 30, antutu: 30, storage: 40, weight: 40, charging: 30, screen_ratio: 20 },
  performance: { price: 20, battery: 50, camera: 50, antutu: 100, storage: 80, weight: 20, charging: 60, screen_ratio: 40 },
  battery_champion: { price: 40, battery: 100, camera: 40, antutu: 30, storage: 40, weight: 30, charging: 80, screen_ratio: 30 },
};

const PRESET_LABELS: Record<string, { label: string; icon: string }> = {
  balanced: { label: 'Balanced', icon: '⚖️' },
  camera_lover: { label: 'Camera Lover', icon: '📸' },
  budget: { label: 'Budget Conscious', icon: '💰' },
  performance: { label: 'Performance First', icon: '🚀' },
  battery_champion: { label: 'Battery Champion', icon: '🔋' },
};

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

interface Props {
  onRankingComplete: (data: RankingResponse) => void;
}

export default function PreferencesPage({ onRankingComplete }: Props) {
  const navigate = useNavigate();
  const [values, setValues] = useState<Record<string, number>>(PRESETS.balanced);
  const [activePreset, setActivePreset] = useState('balanced');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const setSlider = (key: string, val: number) => {
    setValues((prev) => ({ ...prev, [key]: val }));
    setActivePreset('');
  };

  const applyPreset = (name: string) => {
    setValues(PRESETS[name]);
    setActivePreset(name);
  };

  const pieData = CRITERIA.map((c) => ({
    name: c.label,
    value: values[c.key] || 1,
  }));

  const handleRun = async () => {
    setLoading(true);
    setError('');
    try {
      const normalized: PreferencesRequest = {
        price: 0.5,
        battery: 0.5,
        camera: 0.5,
        antutu: 0.5,
        storage: 0.5,
        weight: 0.5,
        charging: 0.5,
        screen_ratio: 0.5,
      };
      CRITERIA.forEach((c) => { normalized[c.key] = (values[c.key] || 50) / 100; });
      const { weights } = await submitPreferences(normalized);
      const ranking = await runRanking(weights);
      onRankingComplete(ranking);
      navigate('/results');
    } catch {
      setError('Analysis failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <div className="page-header">
        <h1>Set Your <span className="gradient-text">Priorities</span></h1>
        <p>Adjust the sliders to tell us what matters most to you in a smartphone.</p>
      </div>

      <div className="preferences-layout">
        {/* Sliders panel */}
        <div className="sliders-panel">
          {CRITERIA.map((c) => (
            <div key={c.key} className="glass-card slider-card">
              <div className="slider-header">
                <span className="slider-label">{c.icon} {c.label}</span>
                <span className="slider-value">{values[c.key]}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={values[c.key]}
                onChange={(e) => setSlider(c.key, +e.target.value)}
                id={`slider-${c.key}`}
              />
              <div className="slider-labels-row">
                <span>Not Important</span>
                <span>Very Important</span>
              </div>
            </div>
          ))}
        </div>

        {/* Presets & chart panel */}
        <div className="presets-panel">
          <div className="glass-card-static presets-section">
            <h4>Quick Presets</h4>
            <div className="preset-buttons">
              {Object.entries(PRESET_LABELS).map(([key, { label, icon }]) => (
                <button
                  key={key}
                  className={`preset-btn${activePreset === key ? ' active' : ''}`}
                  onClick={() => applyPreset(key)}
                  id={`preset-${key}`}
                >
                  {icon} {label}
                </button>
              ))}
            </div>
          </div>

          <div className="glass-card-static weight-chart-container">
            <h4>Weight Distribution</h4>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1a1f2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#f8fafc' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="glass-card-static run-analysis-container">
            <button
              className="btn btn-primary btn-lg"
              onClick={handleRun}
              disabled={loading}
              id="btn-run-analysis"
            >
              {loading ? (
                <><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Analyzing...</>
              ) : (
                '🚀 Run Analysis'
              )}
            </button>
            {error && <div className="error-message" style={{ marginTop: 12 }}>{error}</div>}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
