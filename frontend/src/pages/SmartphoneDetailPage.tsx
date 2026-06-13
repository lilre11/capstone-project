import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';

import api from '../api/client';
import type { Smartphone, RankingResponse } from '../types';

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

const TECH_SPEC_LABELS: Record<string, string> = {
  display: 'Display',
  resolution: 'Resolution',
  chipset: 'Chipset',
  ram: 'RAM',
  os: 'OS',
  main_camera: 'Main Camera',
  ultrawide_camera: 'Ultrawide',
  telephoto_camera: 'Telephoto',
  ip_rating: 'IP Rating',
  dimensions: 'Dimensions',
};

const BRAND_COLORS: Record<string, string> = {
  Apple: '#555',
  Samsung: '#1428a0',
  Oppo: '#1d7e3b',
  Asus: '#0b7c46',
  OnePlus: '#eb0029',
  Xiaomi: '#ff6900',
  Nothing: '#000',
};

function formatPrice(price: number): string {
  return new Intl.NumberFormat('tr-TR').format(price) + ' TRY';
}

interface Props {
  rankingData: RankingResponse | null;
}

export default function SmartphoneDetailPage({ rankingData }: Props) {
  const { id } = useParams<{ id: string }>();
  const [phone, setPhone] = useState<Smartphone | null>(null);
  const [loading, setLoading] = useState(true);
  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.get<Smartphone>(`/api/smartphones/${id}`).then((res) => {
      setPhone(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="page-header"><p>Loading...</p></div>;
  }

  if (!phone) {
    return (
      <div className="page-header">
        <h1>Phone Not Found</h1>
        <Link to="/phones" className="btn btn-secondary mt-xl">Back to Smartphones</Link>
      </div>
    );
  }

  const defaultScore = phone.default_score ?? 0;
  const circumference = 2 * Math.PI * 58;
  const brandColor = BRAND_COLORS[phone.brand] || 'var(--surface-2)';

  const rankingEntry = rankingData?.rankings?.find((r) => r.id === phone.id);

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <Link to="/phones" className="back-link">&larr; All Smartphones</Link>

      <div className="phone-detail-hero">
        <div className="phone-detail-hero-image" style={{ background: brandColor }}>
          {!imgFailed ? (
            <img
              src={phone.image_url}
              alt={phone.model_name}
              className="phone-detail-image"
              onError={() => setImgFailed(true)}
            />
          ) : (
            <div className="phone-detail-image-fallback">
              <span>{phone.brand[0]}</span>
            </div>
          )}
        </div>
        <div className="phone-detail-hero-info">
          <span className="phone-detail-brand">{phone.brand}</span>
          <h1 className="phone-detail-name gradient-text">{phone.model_name}</h1>
          <div className="phone-detail-price">{formatPrice(phone.specs.price)}</div>
        </div>
        <div className="phone-detail-score-ring">
          <svg width="140" height="140" viewBox="0 0 140 140">
            <circle cx="70" cy="70" r="58" fill="none" stroke="var(--surface-2)" strokeWidth="6" />
            <circle
              cx="70" cy="70" r="58" fill="none"
              stroke="var(--primary)" strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - defaultScore / 100)}
              transform="rotate(-90 70 70)"
            />
          </svg>
          <div className="phone-detail-score-value">
            <span className="phone-detail-score-number">{Math.round(defaultScore)}</span>
            <span className="phone-detail-score-label">/ 100</span>
          </div>
        </div>
      </div>

      <div className="phone-detail-grid">
        <div className="card-static">
          <h3 className="phone-detail-section-title">Tech Specifications</h3>
          <table className="tech-specs-table">
            <tbody>
              {Object.entries(TECH_SPEC_LABELS).map(([key, label]) => {
                const val = phone.tech_specs?.[key];
                return val ? (
                  <tr key={key}>
                    <td className="tech-specs-label">{label}</td>
                    <td className="tech-specs-value">{val}</td>
                  </tr>
                ) : null;
              })}
            </tbody>
          </table>
        </div>

        <div className="card-static">
          <h3 className="phone-detail-section-title">SmartPick Scores</h3>
          <div className="detail-scores-list">
            {Object.entries(CRITERIA_LABELS).map(([key, label]) => {
              const specValue = phone.specs[key as keyof typeof phone.specs];
              if (specValue === undefined) return null;
              const displayVal = key === 'price'
                ? formatPrice(Number(specValue))
                : key === 'battery'
                  ? `${specValue} mAh`
                  : key === 'antutu'
                    ? Number(specValue).toLocaleString('tr-TR')
                    : String(specValue);
              const pct = Math.min((Number(specValue) / 50000) * 100, 100);
              return (
                <div key={key} className="detail-score-row">
                  <div className="detail-score-header">
                    <span className="detail-score-name">{label}</span>
                    <span className="detail-score-raw">{displayVal}</span>
                  </div>
                  <div className="score-bar">
                    <div className="score-bar-track">
                      <div className="score-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {rankingEntry && (
        <div className="card-static phone-detail-ranking-section">
          <h3 className="phone-detail-section-title">Your Ranking</h3>
          <p>
            This phone ranked <strong>#{rankingEntry.rank}</strong> in your last analysis
            with a score of <strong>{rankingEntry.score.toFixed(1)}</strong>
            {' '}(closeness coefficient: {rankingEntry.closeness_coefficient.toFixed(4)}).
          </p>
          <Link to="/results" className="btn btn-secondary mt-md">View Full Results</Link>
        </div>
      )}
    </motion.div>
  );
}
