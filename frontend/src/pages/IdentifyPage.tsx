import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { detectDevice } from '../api/client';
import type { DetectionResponse } from '../types';

// Map model_id → display name
const MODEL_DISPLAY: Record<string, string> = {
  apple_iphone_17_pm: 'iPhone 17 Pro Max',
  samsung_s25_ultra: 'Galaxy S25 Ultra',
  oppo_find_x9_pro: 'Find X9 Pro',
  samsung_galaxy_z_fold_7: 'Galaxy Z Fold 7',
  asus_rog_phone_9_pro: 'ROG Phone 9 Pro',
  oneplus_13: 'OnePlus 13',
  xiaomi_15t: 'Xiaomi 15T',
  apple_iphone_16e: 'iPhone 16e',
  samsung_galaxy_a56_5g: 'Galaxy A56 5G',
  nothing_cmf_phone_2_pro: 'CMF Phone 2 Pro',
};

export default function IdentifyPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragover, setDragover] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DetectionResponse | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [selectedModel, setSelectedModel] = useState<'model1' | 'model2'>('model1');

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please upload a JPG or PNG image.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File must be under 10 MB.');
      return;
    }
    setError('');
    setPreview(URL.createObjectURL(file));
    setLoading(true);
    try {
      const res = await detectDevice(file, selectedModel);
      setResult(res);
    } catch {
      setError('Detection failed. Please try another image.');
    } finally {
      setLoading(false);
    }
  }, [selectedModel]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragover(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const reset = () => {
    setResult(null);
    setPreview(null);
    setError('');
  };

  const displayName = result
    ? MODEL_DISPLAY[result.model_id] || result.model_id.replace(/_/g, ' ')
    : '';

  return (
    <motion.div
      className="identify-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="page-header">
        <h1>Identify Your <span className="gradient-text">Device</span></h1>
        <p>Upload a smartphone photo and our YOLO model will detect the model.</p>
      </div>

      {!result ? (
        <>
          <div className="model-selector glass-card">
            <span className="model-label">Model</span>
            <select
              className="model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value as 'model1' | 'model2')}
            >
              <option value="model1">Model 1</option>
              <option value="model2">Model 2</option>
            </select>
          </div>

        <div
          className={`upload-zone${dragover ? ' dragover' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
          onDragLeave={() => setDragover(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
          {loading ? (
            <div className="spinner-container">
              <div className="spinner" />
              <p className="spinner-text">Analyzing image...</p>
            </div>
          ) : (
            <>
              <div className="upload-icon">📤</div>
              <h3>Drag & drop your smartphone photo</h3>
              <p>or click to browse files</p>
              <p className="upload-hint">Supports JPG, PNG — Max 10 MB</p>
            </>
          )}
        </div>
        </>
      ) : (
        <div className="glass-card detection-result">
          {preview && <img src={preview} alt="Uploaded" />}
          <div className="badge badge-green" style={{ marginBottom: 16 }}>
            ✓ Device Detected
          </div>
          <div className="detection-model gradient-text">{displayName}</div>
          <div className="detection-confidence">
            {(result.confidence_score * 100).toFixed(1)}% confidence
          </div>
          <div className="detection-actions">
            <button
              className="btn btn-primary"
              onClick={() => navigate('/preferences')}
            >
              Continue to Analysis →
            </button>
            <button className="btn btn-secondary" onClick={reset}>
              Try Another Photo
            </button>
          </div>
        </div>
      )}

      {error && <div className="error-message" style={{ marginTop: 16 }}>{error}</div>}
    </motion.div>
  );
}
