import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { askExplanation } from '../api/client';
import type { ChatMessage, RankingResponse } from '../types';

interface Props {
  rankingData: RankingResponse | null;
}

export default function ExplainPage({ rankingData }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Send initial greeting
  useEffect(() => {
    if (!rankingData || initialized) return;
    setInitialized(true);
    const sendInitial = async () => {
      setLoading(true);
      try {
        const res = await askExplanation(
          `Briefly explain why ${rankingData.top_match.model_name} was ranked #1 with a score of ${rankingData.top_match.score.toFixed(1)}/100. Mention the top 2-3 factors that contributed most.`,
          rankingData.ranking_id,
        );
        setMessages([{ role: 'assistant', content: res.answer }]);
      } catch {
        setMessages([{
          role: 'assistant',
          content: `Welcome! I can help explain the ranking results. The top recommendation is **${rankingData.top_match.model_name}** with a score of ${rankingData.top_match.score.toFixed(1)}/100. Ask me anything about the results!`,
        }]);
      } finally {
        setLoading(false);
      }
    };
    sendInitial();
  }, [rankingData, initialized]);

  const handleSend = async () => {
    if (!input.trim() || !rankingData || loading) return;
    const question = input.trim();
    setInput('');
    const userMsg: ChatMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const history = [...messages, userMsg].map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const res = await askExplanation(question, rankingData.ranking_id, history);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!rankingData) {
    return (
      <div className="page-header">
        <h1>No Results</h1>
        <p>Run an analysis first to get AI explanations.</p>
        <Link to="/preferences" className="btn btn-primary" style={{ marginTop: 24 }}>Go to Preferences</Link>
      </div>
    );
  }

  return (
    <motion.div
      className="chat-container"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble chat-bubble-${msg.role === 'assistant' ? 'ai' : 'user'}`}>
            <span className="chat-bubble-label">
              {msg.role === 'assistant' ? '🤖 AI Explainer' : '👤 You'}
            </span>
            {msg.content}
          </div>
        ))}
        {loading && (
          <div className="typing-indicator">
            <span /><span /><span />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-bar">
        <input
          type="text"
          className="input-field"
          placeholder="Ask about the ranking results..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={loading}
          id="chat-input"
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={loading || !input.trim()}
          id="btn-send"
        >
          Send
        </button>
      </div>
    </motion.div>
  );
}
