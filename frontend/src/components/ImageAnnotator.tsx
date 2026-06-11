import { useRef, useEffect, useState } from 'react';
import type { Detection } from '../types';

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

interface Props {
  src: string;
  detections: Detection[];
  imageWidth: number;
  imageHeight: number;
}

export default function ImageAnnotator({ src, detections, imageWidth, imageHeight }: Props) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgNatural, setImgNatural] = useState({ w: 0, h: 0 });

  useEffect(() => {
    setImgLoaded(false);
    setImgNatural({ w: 0, h: 0 });
  }, [src]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !imgLoaded || detections.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const displayW = img.clientWidth;
    const displayH = img.clientHeight;

    canvas.width = displayW * dpr;
    canvas.height = displayH * dpr;
    canvas.style.width = `${displayW}px`;
    canvas.style.height = `${displayH}px`;
    ctx.scale(dpr, dpr);

    const scaleX = displayW / imageWidth;
    const scaleY = displayH / imageHeight;

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
  }, [detections, imageWidth, imageHeight, imgLoaded, imgNatural]);

  return (
    <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%' }}>
      <img
        ref={imgRef}
        src={src}
        alt="Uploaded device"
        style={{ display: 'block', maxWidth: '100%', height: 'auto', borderRadius: 12 }}
        onLoad={() => {
          setImgLoaded(true);
          if (imgRef.current) {
            setImgNatural({ w: imgRef.current.naturalWidth, h: imgRef.current.naturalHeight });
          }
        }}
        crossOrigin="anonymous"
      />
      {detections.length > 0 && (
        <canvas
          ref={canvasRef}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            pointerEvents: 'none',
            borderRadius: 12,
          }}
        />
      )}
    </div>
  );
}
