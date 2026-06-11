import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getArtifacts } from '../api/client';
import type { ArtifactsResponse } from '../api/client';

const MODEL_LABELS: Record<string, string> = {
  model_1: 'Model 1 (yolo11n, 1024px)',
  model_2: 'Model 2 (yolo11s, 640px)',
  model_3: 'Model 3 (yolo11s, 640px, cos_lr)',
};

const GALLERY_LABELS: Record<string, string> = {
  confusion_matrix_normalized: 'Normalized Confusion Matrix',
  BoxPR_curve: 'Precision-Recall Curve',
  BoxF1_curve: 'F1 Confidence Curve',
  BoxP_curve: 'Precision Curve',
  BoxR_curve: 'Recall Curve',
  results: 'Training Results',
};

const METRIC_LABELS: Record<string, string> = {
  'metrics/precision(B)': 'Precision',
  'metrics/recall(B)': 'Recall',
  'metrics/mAP50(B)': 'mAP@50',
  'metrics/mAP50-95(B)': 'mAP@50-95',
};

function lastEpochMetrics(metrics: Record<string, number | string> | null) {
  if (!metrics) return null;
  const out: Record<string, string> = {};
  for (const [key, label] of Object.entries(METRIC_LABELS)) {
    const val = metrics[key];
    if (val !== undefined) {
      const num = typeof val === 'string' ? parseFloat(val) : val;
      out[label] = (num * 100).toFixed(1) + '%';
    }
  }
  return out;
}

export default function ModelPerformancePage() {
  const [data, setData] = useState<ArtifactsResponse | null>(null);
  const [activeModel, setActiveModel] = useState('model_3');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  useEffect(() => {
    getArtifacts().then(setData).catch(() => {});
  }, []);

  const modelNames = data ? Object.keys(data).sort() : [];
  const active = data?.[activeModel] ?? null;
  const parsed = active ? lastEpochMetrics(active.metrics) : null;

  const modelList = modelNames.length
    ? modelNames
    : ['model_1', 'model_2', 'model_3'];

  return (
    <motion.div
      className="model-perf-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="page-header">
        <h1>Model <span className="gradient-text">Performance</span></h1>
        <p>Training metrics and visualizations for all YOLO models.</p>
      </div>

      <div className="model-selector card">
        <span className="model-label">Model</span>
        <select
          className="model-select"
          value={activeModel}
          onChange={(e) => { setActiveModel(e.target.value); setSelectedImage(null); }}
        >
          {modelList.map((name) => (
            <option key={name} value={name}>
              {MODEL_LABELS[name] || name}
            </option>
          ))}
        </select>
      </div>

      {parsed && (
        <div className="metrics-grid">
          {Object.entries(parsed).map(([label, value]) => (
            <div key={label} className="card metric-card">
              <div className="metric-value gradient-text">{value}</div>
              <div className="metric-label">{label}</div>
            </div>
          ))}
        </div>
      )}

      {active && active.images.length > 0 && (
        <div className="gallery-grid">
          {active.images.map((img) => {
            const baseKey =
              img.replace('.png', '').replace('.jpg', '').replace('.jpeg', '');
            const label =
              GALLERY_LABELS[baseKey] ||
              baseKey.replace(/_/g, ' ');
            const imgUrl =
              activeModel === 'model_3'
                ? `http://localhost:8000/artifacts/model_3/runs/${img}`
                : `http://localhost:8000/artifacts/${activeModel}/${img}`;

            return (
              <motion.div
                key={img}
                className="card gallery-card"
                whileHover={{ scale: 1.02 }}
                onClick={() => setSelectedImage(imgUrl)}
              >
                <img
                  src={imgUrl}
                  alt={label}
                  className="gallery-thumb"
                  loading="lazy"
                />
                <div className="gallery-label">{label}</div>
              </motion.div>
            );
          })}
        </div>
      )}

      {!active && (
        <div className="card" style={{ padding: '32px', textAlign: 'center' }}>
          <p>No artifacts found for this model.</p>
        </div>
      )}

      {selectedImage && (
        <div
          className="lightbox-overlay"
          onClick={() => setSelectedImage(null)}
        >
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <img src={selectedImage} alt="Full size" className="lightbox-img" />
            <button
              className="lightbox-close"
              onClick={() => setSelectedImage(null)}
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
