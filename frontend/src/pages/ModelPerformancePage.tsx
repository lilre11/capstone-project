import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getArtifacts } from '../api/client';
import type { ArtifactsResponse } from '../api/client';

const MODEL_LABELS: Record<string, string> = {
  model_1: 'YOLO11n (1024px)',
  model_2: 'YOLO11s (640px)',
  model_3: 'YOLO11s (640px, cos_lr)',
};

const MODEL_DESCRIPTIONS: Record<string, string> = {
  model_1: 'Nano variant — fast inference, lower accuracy',
  model_2: 'Small variant — balanced speed and accuracy',
  model_3: 'Small variant with cosine LR scheduler',
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

      <div className="model-picker card">
        <span className="model-picker-label">Select Model</span>
        <div className="model-picker-options">
          {modelList.map((name) => (
            <button
              key={name}
              className={`model-picker-btn${activeModel === name ? ' active' : ''}`}
              onClick={() => { setActiveModel(name); setSelectedImage(null); }}
            >
              <span className="model-picker-btn-label">{MODEL_LABELS[name] || name}</span>
              <span className="model-picker-btn-desc">{MODEL_DESCRIPTIONS[name] || ''}</span>
            </button>
          ))}
        </div>
      </div>

      {parsed && (
        <div className="metrics-grid">
          {Object.entries(parsed).map(([label, value], i) => (
            <motion.div
              key={label}
              className="metric-card"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.3 }}
            >
              <div className="metric-value gradient-text">{value}</div>
              <div className="metric-label">{label}</div>
            </motion.div>
          ))}
        </div>
      )}

      {active && active.images.length > 0 && (
        <>
          <h3 className="section-subtitle">Visualizations</h3>
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
                  className="gallery-card"
                  layout
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35 }}
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
        </>
      )}

      {!active && (
        <motion.div
          className="card-static"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ padding: '48px 32px', textAlign: 'center' }}
        >
          <p style={{ color: 'var(--ink-muted)' }}>No training artifacts found for this model.</p>
        </motion.div>
      )}

      <AnimatePresence>
        {selectedImage && (
          <motion.div
            className="lightbox-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedImage(null)}
          >
            <motion.div
              className="lightbox-content"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={(e) => e.stopPropagation()}
            >
              <img src={selectedImage} alt="Full size" className="lightbox-img" />
              <button
                className="lightbox-close"
                onClick={() => setSelectedImage(null)}
              >
                Close ✕
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
