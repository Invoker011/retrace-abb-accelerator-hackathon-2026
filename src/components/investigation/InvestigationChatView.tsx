import React, { useState, useRef, useEffect } from 'react';
import {
  ChatMessage,
  Evidence,
} from '../../types';
import { FindingBadge } from '../common/FindingBadge';
import { investigationService } from '../../services/investigationService';
import {
  Send,
  Sparkles,
  Bot,
  User,
  ShieldCheck,
  FileSpreadsheet,
  AlertCircle,
  HelpCircle,
  RotateCcw,
} from 'lucide-react';

interface InvestigationChatViewProps {
  evidenceList: Evidence[];
  onSelectEvidence: (evidence: Evidence) => void;
}

export const InvestigationChatView: React.FC<InvestigationChatViewProps> = ({
  evidenceList,
  onSelectEvidence,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load initial conversation and suggested questions from service
    investigationService.getInitialConversation('INC-2026-001').then((msgs) => {
      setMessages(msgs);
    });
    investigationService.getSuggestedQuestions().then((qs) => {
      setSuggestedQuestions(qs);
    });
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || isTyping) return;

    const userMsg: ChatMessage = {
      id: `USER-${Date.now()}`,
      sender: 'technician',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsTyping(true);

    try {
      // Query investigation service
      setTimeout(async () => {
        const reply = await investigationService.queryInvestigation('INC-2026-001', textToSend);
        setMessages((prev) => [...prev, reply]);
        setIsTyping(false);
      }, 600);
    } catch (e) {
      setIsTyping(false);
    }
  };

  const handleResetChat = async () => {
    const initial = await investigationService.getInitialConversation('INC-2026-001');
    setMessages(initial);
  };

  return (
    <div
      id="investigation-chat-workspace"
      className="p-8 max-w-5xl mx-auto h-[calc(100vh-4rem)] flex flex-col justify-between space-y-4"
    >
      {/* Header bar */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">
              Technician Troubleshooting Intelligence
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300 font-mono">
              Advisory Decision Support
            </span>
          </div>
          <h1 className="text-xl font-bold font-mono text-white mt-1">
            Incident Investigation Copilot
          </h1>
          <p className="text-xs text-slate-400">
            Grounded on 6 multimodal evidence sources for Incident INC-2026-001 (Pump P-204)
          </p>
        </div>

        <button
          onClick={handleResetChat}
          title="Reset conversation to initial sample"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Context</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-2">
        {messages.map((msg) => {
          const isTechnician = msg.sender === 'technician';
          return (
            <div
              key={msg.id}
              className={`flex gap-3.5 ${
                isTechnician ? 'justify-end' : 'justify-start'
              }`}
            >
              {!isTechnician && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-600 to-blue-700 flex items-center justify-center text-white shrink-0 shadow-md">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-xl p-4.5 space-y-3 ${
                  isTechnician
                    ? 'bg-blue-600/20 border border-blue-500/40 text-blue-50'
                    : 'bg-[#0b101c] border border-slate-800 text-slate-200 shadow-lg'
                }`}
              >
                {/* Message Header */}
                <div className="flex items-center justify-between gap-3 text-xs font-mono">
                  <span className={`font-semibold ${isTechnician ? 'text-blue-300' : 'text-cyan-400'}`}>
                    {isTechnician ? 'Technician' : 'RETRACE Intelligence'}
                  </span>
                  <span className="text-slate-500 text-[10px]">{msg.timestamp}</span>
                </div>

                {/* Finding category badge if attached */}
                {msg.findingReferenceCategory && (
                  <div>
                    <FindingBadge category={msg.findingReferenceCategory} size="sm" />
                  </div>
                )}

                {/* Content */}
                <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap font-sans text-slate-200">
                  {msg.content}
                </div>

                {/* Supporting Evidence Attachments */}
                {msg.supportingEvidence && msg.supportingEvidence.length > 0 && (
                  <div className="pt-3 border-t border-slate-800/80 space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-mono text-cyan-400">
                      <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Supporting Evidence Records:</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {msg.supportingEvidence.map((evItem) => {
                        const fullEv = evidenceList.find((e) => e.id === evItem.id);
                        return (
                          <div
                            key={evItem.id}
                            onClick={() => fullEv && onSelectEvidence(fullEv)}
                            className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-cyan-700/60 transition-all cursor-pointer group text-xs font-mono"
                          >
                            <div className="flex items-center justify-between text-cyan-300 group-hover:underline font-bold text-[11px]">
                              <span className="flex items-center gap-1.5">
                                <FileSpreadsheet className="w-3.5 h-3.5 text-cyan-400" />
                                {evItem.filename}
                              </span>
                              <span className="text-[10px] text-slate-500 font-normal">
                                Inspect →
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 font-sans mt-1 line-clamp-1">
                              {evItem.summary}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {isTechnician && (
                <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {isTyping && (
          <div className="flex gap-3.5 items-center text-slate-400 text-xs font-mono pl-1">
            <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400">
              <Sparkles className="w-4 h-4 animate-spin" />
            </div>
            <span className="animate-pulse">Cross-referencing multimodal evidence records...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Questions Section */}
      <div className="pt-2 shrink-0 space-y-2">
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
          <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
          <span>Suggested Investigation Questions:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {suggestedQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900/80 hover:bg-cyan-950/60 border border-slate-800 hover:border-cyan-800/80 text-xs font-mono text-slate-300 hover:text-cyan-300 transition-all text-left"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form & Safety Notice */}
      <div className="shrink-0 space-y-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            id="chat-query-input"
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask questions about Pump P-204 shutdown sequence, assets, or evidence..."
            className="flex-1 px-4 py-3 rounded-xl bg-[#090f1d] border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-sans"
          />
          <button
            id="chat-send-btn"
            type="submit"
            disabled={!inputQuery.trim() || isTyping}
            className="px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 disabled:hover:bg-cyan-600 text-white font-mono text-xs font-bold flex items-center gap-2 transition-all shrink-0"
          >
            <span>Ask</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 px-1">
          <span className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-slate-500" />
            Advisory decision support only • Requires human engineering review
          </span>
          <span>Never executes machine actuation</span>
        </div>
      </div>
    </div>
  );
};
