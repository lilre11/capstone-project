import { useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';

import Layout from './components/Layout';
import LandingPage from './pages/LandingPage';
import IdentifyPage from './pages/IdentifyPage';
import PreferencesPage from './pages/PreferencesPage';
import ResultPage from './pages/ResultPage';
import RankingsPage from './pages/RankingsPage';
import ComparePage from './pages/ComparePage';
import ExplainPage from './pages/ExplainPage';
import ChatbotPage from './pages/ChatbotPage';
import type { RankingResponse } from './types';

export default function App() {
  const location = useLocation();
  const [rankingData, setRankingData] = useState<RankingResponse | null>(null);

  return (
    <Layout>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/identify" element={<IdentifyPage />} />
          <Route
            path="/preferences"
            element={<PreferencesPage onRankingComplete={setRankingData} />}
          />
          <Route path="/results" element={<ResultPage rankingData={rankingData} />} />
          <Route path="/rankings" element={<RankingsPage rankingData={rankingData} />} />
          <Route path="/compare" element={<ComparePage rankingData={rankingData} />} />
          <Route path="/chat" element={<ChatbotPage rankingData={rankingData} />} />
          <Route path="/explain" element={<ExplainPage rankingData={rankingData} />} />
        </Routes>
      </AnimatePresence>
    </Layout>
  );
}
