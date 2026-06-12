import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

import { getSmartphones } from '../api/client';
import type { Smartphone } from '../types';

function formatPrice(price: number): string {
  return new Intl.NumberFormat('tr-TR').format(price) + ' TRY';
}

const BRAND_COLORS: Record<string, string> = {
  Apple: '#555',
  Samsung: '#1428a0',
  Oppo: '#1d7e3b',
  Asus: '#0b7c46',
  OnePlus: '#eb0029',
  Xiaomi: '#ff6900',
  Nothing: '#000',
};

export default function SmartphonesPage() {
  const [phones, setPhones] = useState<Smartphone[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSmartphones().then((res) => {
      setPhones(res.smartphones);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="page-header"><p>Loading smartphones...</p></div>;
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-header">
        <h1>All <span className="gradient-text">Smartphones</span></h1>
        <p>Browse specs, compare scores, and see how each phone ranks.</p>
      </div>

      <div className="phones-grid">
        {phones.map((phone, i) => (
          <motion.div
            key={phone.id}
            className="phone-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.35 }}
          >
            <Link to={`/phones/${phone.id}`} className="phone-card-link">
              <div className="phone-card-image-wrap" style={{ background: BRAND_COLORS[phone.brand] || 'var(--surface-2)' }}>
                <img
                  src={phone.image_url}
                  alt={phone.model_name}
                  className="phone-card-image"
                  loading="lazy"
                  onError={(e) => {
                    const target = e.currentTarget;
                    target.style.display = 'none';
                    const fallback = target.nextElementSibling;
                    if (fallback) (fallback as HTMLElement).style.display = 'flex';
                  }}
                />
                <div className="phone-card-image-fallback" style={{ display: 'none' }}>
                  <span>{phone.brand[0]}</span>
                </div>
                <div className="phone-card-score-badge">
                  <svg width="44" height="44" viewBox="0 0 44 44">
                    <circle cx="22" cy="22" r="19" fill="var(--canvas)" stroke="var(--hairline)" strokeWidth="2" />
                    <circle
                      cx="22" cy="22" r="19" fill="none"
                      stroke="var(--primary)" strokeWidth="3"
                      strokeLinecap="round"
                      strokeDasharray={119.38}
                      strokeDashoffset={119.38 * (1 - (phone.default_score ?? 0) / 100)}
                      transform="rotate(-90 22 22)"
                    />
                  </svg>
                  <span className="phone-card-score-text">{Math.round(phone.default_score ?? 0)}</span>
                </div>
              </div>

              <div className="phone-card-body">
                <span className="phone-card-brand">{phone.brand}</span>
                <h3 className="phone-card-model">{phone.model_name}</h3>

                <div className="phone-card-specs">
                  <div className="phone-card-spec">
                    <span className="phone-card-spec-label">Price</span>
                    <span className="phone-card-spec-value">{formatPrice(phone.specs.price)}</span>
                  </div>
                  <div className="phone-card-spec">
                    <span className="phone-card-spec-label">Battery</span>
                    <span className="phone-card-spec-value">{phone.specs.battery_mah} mAh</span>
                  </div>
                  <div className="phone-card-spec">
                    <span className="phone-card-spec-label">Camera</span>
                    <span className="phone-card-spec-value">{phone.specs.camera_score}</span>
                  </div>
                  <div className="phone-card-spec">
                    <span className="phone-card-spec-label">Performance</span>
                    <span className="phone-card-spec-value">{phone.specs.antutu_score.toLocaleString('tr-TR')}</span>
                  </div>
                </div>

                <div className="phone-card-chips">
                  {phone.specs.storage_gb && <span className="phone-card-chip">{phone.specs.storage_gb} GB</span>}
                  {phone.specs.charging_watts && <span className="phone-card-chip">{phone.specs.charging_watts}W</span>}
                  {phone.tech_specs?.ram && <span className="phone-card-chip">{phone.tech_specs.ram}</span>}
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
