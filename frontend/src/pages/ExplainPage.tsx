import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { askExplanation } from '../api/client';
import type { ChatMessage, RankingResponse } from '../types';

interface Props {
  rankingData: RankingResponse | null;
}

const MODEL_LABELS: Record<string, string> = {
  'openrouter/free': 'Auto (Free Router)',
  'google/gemma-4-31b-it:free': 'Gemma 4 31B',
  'meta-llama/llama-3.3-70b-instruct:free': 'Llama 3.3 70B',
  'openai/gpt-oss-120b:free': 'GPT OSS 120B',
  'qwen/qwen3-next-80b-a3b-instruct:free': 'Qwen3 Next 80B',
};

const EXPLAIN_MODELS = [
  { value: 'openrouter/free', label: 'Auto (Free Router)' },
  { value: 'google/gemma-4-31b-it:free', label: 'Gemma 4 31B' },
  { value: 'meta-llama/llama-3.3-70b-instruct:free', label: 'Llama 3.3 70B' },
  { value: 'openai/gpt-oss-120b:free', label: 'GPT OSS 120B' },
  { value: 'qwen/qwen3-next-80b-a3b-instruct:free', label: 'Qwen3 Next 80B' },
];

export default function ExplainPage({ rankingData }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('openrouter/free');
  const initializedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Send initial greeting
  useEffect(() => {
    if (!rankingData || initializedRef.current) return;
    initializedRef.current = true;
    const sendInitial = async () => {
      setLoading(true);
      try {
        const res = await askExplanation(
          `Briefly explain why ${rankingData.top_match.model_name} was ranked #1 with a score of ${rankingData.top_match.score.toFixed(1)}/100. Mention the top 2-3 factors that contributed most.`,
          rankingData.ranking_id,
          undefined,
          selectedModel,
        );
        const modelLabel = MODEL_LABELS[res.model_used] || res.model_used;
        const content = res.model_used === 'template_fallback'
          ? res.answer
          : `[${modelLabel}]\n\n${res.answer}`;
        setMessages([{ role: 'assistant', content: content }]);
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
  }, [rankingData, selectedModel]);

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
      const res = await askExplanation(question, rankingData.ranking_id, history, selectedModel);
      const modelLabel = MODEL_LABELS[res.model_used] || res.model_used;
      const content = res.model_used === 'template_fallback'
        ? res.answer
        : `[${modelLabel}]\n\n${res.answer}`;
      setMessages((prev) => [...prev, { role: 'assistant', content: content }]);
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
        <Link to="/preferences" className="btn btn-primary mt-xl">Go to Preferences</Link>
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
      <div className="chatbot-toolbar">
        <label className="chatbot-model-picker">
          <span className="chatbot-model-label">Free model</span>
          <select
            className="chatbot-model-select"
            value={selectedModel}
            onChange={(event) => {
              initializedRef.current = false;
              setSelectedModel(event.target.value);
            }}
            disabled={loading}
          >
            {EXPLAIN_MODELS.map((model) => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble chat-bubble-${msg.role === 'assistant' ? 'ai' : 'user'}`}>
            <span className="chat-bubble-label">
              {msg.role === 'assistant' ? 'SmartPick AI' : 'You'}
            </span>
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        ))}
        {loading && (
          <div className="typing-indicator">
            <div className="typing-indicator-bar" />
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
