import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

import { askChatbot } from '../api/client';
import type { ChatMessage, RankingResponse } from '../types';

interface Props {
  rankingData: RankingResponse | null;
}

const GENERAL_PROMPTS = [
  'What kind of phone is best for battery life?',
  'Which phones look strongest for gaming?',
  'How should I balance camera and price?',
];

const RANKING_PROMPTS = [
  'Why did the top phone rank first?',
  'Compare the top 2 phones for me.',
  'Which criterion affected the result most?',
];

const MODEL_LABELS: Record<string, string> = {
  'openrouter/free': 'OpenRouter (Auto)',
  'llama-3.3-70b-versatile': 'Groq Llama 3.3 70B',
  'llama-3.1-8b-instant': 'Groq Llama 3.1 8B',
  'meta-llama/llama-4-scout-17b-16e-instruct': 'Groq Llama 4 Scout 17B',
  'qwen/qwen3-32b': 'Groq Qwen3 32B',
};

const CHAT_MODELS = [
  { value: 'openrouter/free', label: 'OpenRouter (Auto)' },
  { value: 'llama-3.3-70b-versatile', label: 'Groq Llama 3.3 70B' },
  { value: 'llama-3.1-8b-instant', label: 'Groq Llama 3.1 8B' },
  { value: 'meta-llama/llama-4-scout-17b-16e-instruct', label: 'Groq Llama 4 Scout 17B' },
  { value: 'qwen/qwen3-32b', label: 'Groq Qwen3 32B' },
];

export default function ChatbotPage({ rankingData }: Props) {
  const initialMessage = rankingData
    ? `I can explain your scores, rankings, trade-offs, and comparisons. Your current top match is ${rankingData.top_match.model_name}.`
    : 'I can help with general smartphone guidance using the app data. Run an analysis anytime and I will become more specific about your rankings.';
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: initialMessage },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('openrouter/free');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const starterPrompts = rankingData ? RANKING_PROMPTS : GENERAL_PROMPTS;

  async function sendQuestion(question: string) {
    if (!question.trim() || loading) return;

    const trimmed = question.trim();
    const userMessage: ChatMessage = { role: 'user', content: trimmed };
    const nextHistory = [...messages, userMessage];

    setMessages(nextHistory);
    setInput('');
    setLoading(true);

    try {
      const response = await askChatbot(
        trimmed,
        rankingData?.ranking_id,
        nextHistory,
        selectedModel,
      );
      const modelUsed = response.model_used === 'template_fallback' ? undefined : response.model_used;
      const content = response.answer;
      setMessages((prev) => [...prev, { role: 'assistant', content, model_used: modelUsed }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'I could not reach the chatbot right now. Please try again in a moment.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      className="chatbot-page"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="page-header">
        <h1>
          Smartphone <span className="gradient-text">Chatbot</span>
        </h1>
        <p>
          Ask open-ended smartphone questions, or use your saved ranking context for
          explanation and comparison.
        </p>
        {!rankingData && (
          <Link to="/preferences" className="btn btn-secondary mt-xl">
            Run Analysis First
          </Link>
        )}
      </div>

      <div className="chatbot-shell card-static">
        <div className="chatbot-toolbar">
          <label className="chatbot-model-picker">
            <span className="chatbot-model-label">Chat model</span>
            <select
              className="chatbot-model-select"
              value={selectedModel}
              onChange={(event) => setSelectedModel(event.target.value)}
              disabled={loading}
            >
              {CHAT_MODELS.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="chatbot-prompts">
          {starterPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="chatbot-prompt-chip"
              onClick={() => void sendQuestion(prompt)}
              disabled={loading}
            >
              {prompt}
            </button>
          ))}
        </div>

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div
              key={`${msg.role}-${index}`}
              className={`chat-bubble chat-bubble-${msg.role === 'assistant' ? 'ai' : 'user'}`}
            >
              <span className="chat-bubble-label">
                {msg.role === 'assistant' ? 'SmartPick AI' : 'You'}
                {msg.model_used && (
                  <span className="chat-bubble-model">
                    {MODEL_LABELS[msg.model_used] || msg.model_used}
                  </span>
                )}
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

        <div className="chat-input-bar">
          <input
            type="text"
            className="input-field"
            placeholder="Ask about smartphones, scores, or comparisons..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                void sendQuestion(input);
              }
            }}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={() => void sendQuestion(input)}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </motion.div>
  );
}
