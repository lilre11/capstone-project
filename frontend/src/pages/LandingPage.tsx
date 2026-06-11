import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.15, duration: 0.6, ease: 'easeOut' as const },
  }),
};

const features = [
  { title: 'YOLOv8 Detection', desc: 'Upload a photo and our YOLO model identifies the smartphone model instantly.' },
  { title: 'TOPSIS Ranking', desc: 'AHP weights your priorities, TOPSIS ranks phones against the ideal solution.' },
  { title: 'LLM Explainer', desc: 'Ask the AI why a phone was recommended and get plain-language answers.' },
];

export default function LandingPage() {
  return (
    <section className="landing-hero">
      <motion.div
        className="badge badge-primary"
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        style={{ marginBottom: 24 }}
      >
        AI-Powered Decision Support
      </motion.div>

      <motion.h1
        custom={0}
        initial="hidden"
        animate="visible"
        variants={fadeUp}
      >
        Find Your Perfect{' '}
        <span className="gradient-text">Smartphone</span>
      </motion.h1>

      <motion.p
        className="subtitle"
        custom={1}
        initial="hidden"
        animate="visible"
        variants={fadeUp}
      >
        Upload a phone image for AI detection, set your priorities, and let
        our AHP&nbsp;+&nbsp;TOPSIS engine rank the top 10 smartphones for you —
        then ask the AI to explain why.
      </motion.p>

      <motion.div
        className="landing-cta-group"
        custom={2}
        initial="hidden"
        animate="visible"
        variants={fadeUp}
      >
        <Link to="/preferences" className="btn btn-primary btn-lg" id="cta-start">
          Start Analysis
        </Link>
        <Link to="/identify" className="btn btn-secondary btn-lg" id="cta-identify">
          Identify Device
        </Link>
      </motion.div>

      <motion.div
        className="landing-features"
        custom={3}
        initial="hidden"
        animate="visible"
        variants={fadeUp}
      >
        {features.map((f) => (
          <div key={f.title} className="card landing-feature-card">
            <div className="feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
              </svg>
            </div>
            <h3>{f.title}</h3>
            <p>{f.desc}</p>
          </div>
        ))}
      </motion.div>
    </section>
  );
}
