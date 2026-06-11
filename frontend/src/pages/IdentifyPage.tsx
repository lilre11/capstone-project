import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { detectDevice } from '../api/client';
import ImageAnnotator from '../components/ImageAnnotator';
import type { DetectionResponse, Detection } from '../types';

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

const CLASS_COLORS: Record<string, string> = {
  samsung_s25_ultra: '#FF6B6B',
  apple_iphone_17_pm: '#4ECDC4',
  oppo_find_x9_pro: '#45B7D1',
  samsung_galaxy_z_fold_7: '#96CEB4',
  asus_rog_phone_9_pro: '#FFEAA7',
  oneplus_13: '#DDA0DD',
  xiaomi_15t: '#98D8C8',
  apple_iphone_16e: '#F7DC6F',
  samsung_galaxy_a56_5g: '#BB8FCE',
  nothing_cmf_phone_2_pro: '#85C1E9',
};

function getColor(label: string, index: number): string {
  if (CLASS_COLORS[label]) return CLASS_COLORS[label];
  const hue = (index * 137.5) % 360;
  return `hsl(${hue}, 70%, 55%)`;
}

function drawDetections(
  ctx: CanvasRenderingContext2D,
  detections: Detection[],
  displayW: number,
  displayH: number,
  imageW: number,
  imageH: number,
) {
  const scaleX = displayW / imageW;
  const scaleY = displayH / imageH;

  detections.forEach((det, i) => {
    const color = getColor(det.class, i);
    const { x, y, width, height } = det.bbox;

    const rx = (x - width / 2) * scaleX;
    const ry = (y - height / 2) * scaleY;
    const rw = width * scaleX;
    const rh = height * scaleY;

    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, Math.min(4, displayW / 200));
    ctx.strokeRect(rx, ry, rw, rh);

    const label = `${det.class.replace(/_/g, ' ')} ${(det.confidence * 100).toFixed(0)}%`;
    ctx.font = `bold ${Math.max(11, Math.min(14, displayW / 50))}px Inter, sans-serif`;
    const textMetrics = ctx.measureText(label);
    const textPad = 4;
    const textH = 20;
    const labelY = ry - textH > 0 ? ry - textH : ry + rh;

    ctx.fillStyle = color;
    ctx.fillRect(rx, labelY, textMetrics.width + textPad * 2, textH);
    ctx.fillStyle = '#1a1a2e';
    ctx.fillText(label, rx + textPad, labelY + textH - 5);
  });
}

const MODEL_OPTIONS = [
  { value: 'model1', label: 'Model 1' },
  { value: 'model2', label: 'Model 2' },
  { value: 'model3', label: 'Model 3' },
] as const;

type SelectableModel = (typeof MODEL_OPTIONS)[number]['value'];
const DEFAULT_MODEL = MODEL_OPTIONS[MODEL_OPTIONS.length - 1].value;

export default function IdentifyPage() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const frameCanvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const sendingRef = useRef(false);
  const frameTimerRef = useRef(0);
  const liveDetectionsRef = useRef<Detection[]>([]);
  const liveImageSizeRef = useRef({ w: 0, h: 0 });
  const [dragover, setDragover] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DetectionResponse | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [selectedModel, setSelectedModel] = useState<SelectableModel>(DEFAULT_MODEL);
  const [cameraMode, setCameraMode] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [liveDetections, setLiveDetections] = useState<Detection[]>([]);
  const [liveImageSize, setLiveImageSize] = useState({ w: 0, h: 0 });
  const [capturedDetections, setCapturedDetections] = useState<Detection[]>([]);
  const [capturedImageSize, setCapturedImageSize] = useState({ w: 0, h: 0 });
  const [liveModelName, setLiveModelName] = useState('');

  const stopLiveDetection = useCallback(() => {
    clearInterval(frameTimerRef.current);
    sendingRef.current = false;
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      clearInterval(frameTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  const stopCamera = useCallback(() => {
    stopLiveDetection();
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraMode(false);
    setCapturedImage(null);
    setLiveDetections([]);
    setLiveImageSize({ w: 0, h: 0 });
    setLiveModelName('');
  }, [stopLiveDetection]);

  const startLiveDetection = useCallback(() => {
    const wsUrl = `ws://localhost:8000/ws/detect?model=${selectedModel}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      frameTimerRef.current = window.setInterval(() => {
        if (sendingRef.current || !videoRef.current || !frameCanvasRef.current) return;
        const video = videoRef.current;
        const canvas = frameCanvasRef.current;
        canvas.width = 640;
        canvas.height = 480;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.drawImage(video, 0, 0, 640, 480);
        const base64 = canvas.toDataURL('image/jpeg', 0.7).split(',')[1];
        sendingRef.current = true;
        ws.send(JSON.stringify({ type: 'frame', data: base64 }));
      }, 300);
    };

    ws.onmessage = (event) => {
      sendingRef.current = false;
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'detection') {
          const dets = msg.detections || [];
          liveDetectionsRef.current = dets;
          liveImageSizeRef.current = { w: msg.image_width || 640, h: msg.image_height || 480 };
          setLiveDetections(dets);
          setLiveImageSize(liveImageSizeRef.current);
          if (msg.model_id) {
            setLiveModelName(MODEL_DISPLAY[msg.model_id] || msg.model_id.replace(/_/g, ' '));
          }
        }
      } catch {}
    };

    ws.onerror = () => {
      sendingRef.current = false;
      setError('Live detection unavailable. Camera capture only mode.');
    };

    ws.onclose = () => {
      clearInterval(frameTimerRef.current);
      sendingRef.current = false;
    };

    wsRef.current = ws;
  }, [selectedModel]);

  const startCamera = useCallback(async () => {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      streamRef.current = stream;
      setCameraMode(true);
      setCapturedImage(null);
      setLiveDetections([]);
      setLiveImageSize({ w: 0, h: 0 });
      setLiveModelName('');
    } catch {
      setError('Camera access denied or not available. Please use file upload instead.');
    }
  }, []);

  const captureLiveFrame = useCallback(() => {
    const video = videoRef.current;
    const canvas = frameCanvasRef.current;
    if (!video || !canvas) return;

    stopLiveDetection();

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/png');
    setCapturedImage(dataUrl);

    setCapturedDetections(liveDetectionsRef.current);
    setCapturedImageSize(liveImageSizeRef.current);
  }, [stopLiveDetection]);

  const retakeCamera = useCallback(() => {
    setCapturedImage(null);
    setCapturedDetections([]);
    setCapturedImageSize({ w: 0, h: 0 });
    setLiveDetections([]);
    setLiveImageSize({ w: 0, h: 0 });
    setLiveModelName('');
    startLiveDetection();
  }, [startLiveDetection]);

  const dataUrlToFile = useCallback((dataUrl: string): File => {
    const arr = dataUrl.split(',');
    const mime = arr[0].match(/:(.*?);/)![1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) u8arr[n] = bstr.charCodeAt(n);
    return new File([u8arr], 'camera-capture.png', { type: mime });
  }, []);

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

  const submitCameraPhoto = useCallback(() => {
    if (!capturedImage) return;
    const file = dataUrlToFile(capturedImage);
    stopCamera();
    handleFile(file);
  }, [capturedImage, stopCamera, handleFile]);

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

  /* Assign camera stream to video and start live detection when camera activates */
  useEffect(() => {
    if (!cameraMode || !streamRef.current) return;
    const video = videoRef.current;
    if (!video) return;

    video.srcObject = streamRef.current;

    const onReady = () => {
      startLiveDetection();
    };

    if (video.readyState >= 2) {
      startLiveDetection();
    } else {
      video.addEventListener('canplay', onReady);
      return () => video.removeEventListener('canplay', onReady);
    }
  }, [cameraMode, startLiveDetection]);

  /* Overlay canvas: draw live detections on video */
  useEffect(() => {
    const overlay = overlayRef.current;
    const video = videoRef.current;
    if (!overlay || !video || !cameraMode || capturedImage) return;

    const dpr = window.devicePixelRatio || 1;
    const displayW = video.clientWidth;
    const displayH = video.clientHeight;
    if (displayW === 0 || displayH === 0) return;

    overlay.width = displayW * dpr;
    overlay.height = displayH * dpr;
    overlay.style.width = `${displayW}px`;
    overlay.style.height = `${displayH}px`;

    const ctx = overlay.getContext('2d');
    if (!ctx) return;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, displayW, displayH);

    if (liveDetections.length > 0 && liveImageSize.w > 0) {
      drawDetections(ctx, liveDetections, displayW, displayH, liveImageSize.w, liveImageSize.h);
    }
  }, [liveDetections, liveImageSize, cameraMode, capturedImage]);

  return (
    <motion.div
      className="identify-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="page-header">
        <h1>Identify Your <span className="gradient-text">Device</span></h1>
        <p>Upload or capture a smartphone photo and our YOLO model will detect the model.</p>
      </div>

      {!result ? (
        <>
          <div className="model-selector card">
            <span className="model-label">Model</span>
            <select
              className="model-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value as SelectableModel)}
            >
              {MODEL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {cameraMode ? (
            <div className="camera-view">
              {capturedImage ? (
                <>
                  <ImageAnnotator
                    src={capturedImage}
                    detections={capturedDetections}
                    imageWidth={capturedImageSize.w}
                    imageHeight={capturedImageSize.h}
                  />
                  <div className="camera-actions">
                    <button className="btn btn-primary" onClick={submitCameraPhoto}>
                      Use Photo
                    </button>
                    <button className="btn btn-secondary" onClick={retakeCamera}>
                      Retake
                    </button>
                    <button className="btn btn-ghost" onClick={stopCamera}>
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="camera-feed-container">
                    <video ref={videoRef} className="camera-video" autoPlay playsInline muted />
                    <canvas ref={overlayRef} className="camera-overlay" />
                    <canvas ref={frameCanvasRef} hidden />
                  </div>
                  {liveModelName && (
                    <div className="camera-live-label">
                      {liveModelName}
                    </div>
                  )}
                  <div className="camera-actions">
                    <button className="btn btn-primary" onClick={captureLiveFrame}>
                      Capture
                    </button>
                    <button className="btn btn-ghost" onClick={stopCamera}>
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <>
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
                    <h3>Drag & drop your smartphone photo</h3>
                    <p>or click to browse files</p>
                    <p className="upload-hint">Supports JPG, PNG — Max 10 MB</p>
                  </>
                )}
              </div>
              <div className="camera-divider">
                <span className="camera-divider-line" />
                <span className="camera-divider-text">or</span>
                <span className="camera-divider-line" />
              </div>
              <button className="btn btn-secondary camera-start-btn" onClick={startCamera}>
                Use Camera
              </button>
            </>
          )}
        </>
      ) : (
        <div className="card detection-result">
          {preview && (
            <ImageAnnotator
              src={preview}
              detections={result.detections ?? []}
              imageWidth={result.image_width}
              imageHeight={result.image_height}
            />
          )}
          <div className="badge badge-green" style={{ margin: '16px 0' }}>
            Device Detected
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

      {error && <div className="error-message mt-lg">{error}</div>}
    </motion.div>
  );
}
