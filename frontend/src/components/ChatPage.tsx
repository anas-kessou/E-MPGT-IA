import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Paperclip, RotateCcw, Zap, Copy, ShieldAlert, CheckCircle2, AlertTriangle, Clock, FileText, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { sendChatMessage } from '../api/client';
import { Message } from '../types';

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'bot',
      content: `Bonjour. Je suis l'assistant IA du Système **E-MPGT BTP**.\n\nMa base vectorielle contient les normes **NF**, **DTU**, fiches **AQC**, et documents de chantier. Je peux :\n\n- 🔍 Répondre à vos questions techniques avec **sources certifiées**\n- ✅ Vérifier la **conformité DTU** de vos solutions\n- 📊 Générer des **synthèses** de documents\n\nComment puis-je vous aider ?`,
      sources: [],
      conformity: [],
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    const query = input;
    setInput('');
    setIsLoading(true);

    try {
      const data = await sendChatMessage(query);
      const botMsg: Message = {
        role: 'bot',
        content: data.reply,
        sources: data.sources,
        conformity: data.conformity,
        verified_claims: data.verified_claims,
        confidence: data.confidence,
        agent_used: data.agent_used,
        processing_time_ms: data.processing_time_ms,
      };
      setMessages(prev => [...prev, botMsg]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'bot',
        content: '⚠️ Le backend n\'est pas encore démarré. Lancez `docker compose up` puis `uvicorn app.main:app --reload` depuis le dossier `backend/`.',
        sources: [],
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const quickQuestions = [
    'Quelles sont les règles DTU 20.1 pour les murs ?',
    'Vérifier la conformité ITE enduit isolant',
    'Synthèse des pathologies communes AQC 2025',
  ];

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <header className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-surface-secondary/50 backdrop-blur-sm">
        <div>
          <h2 className="text-lg font-bold text-white">Assistant IA BTP</h2>
          <p className="text-xs text-slate-500">RAG Avancé · Multi-Agent · Conformité DTU</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => {
              setMessages([{
                role: 'bot',
                content: `Conversation réinitialisée. Comment puis-je vous aider ?`,
                sources: [],
                conformity: [],
              }]);
            }}
            className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            title="Réinitialiser la conversation"
          >
            <RotateCcw size={18} />
          </button>
          <span className="badge badge-green">
            <Zap size={12} /> Pipeline Actif
          </span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, index) => (
          <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} fade-in`}>
            {msg.role === 'bot' && (
              <div className="w-9 h-9 rounded-xl gradient-brand flex items-center justify-center shrink-0 glow-green">
                <Bot size={18} className="text-white" />
              </div>
            )}

            <div className={`max-w-[75%] ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-bot'} p-5 relative group`}>
              {msg.role === 'user' ? (
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
              ) : (
                <div className="prose-dark text-sm">
                  <button 
                    onClick={() => navigator.clipboard.writeText(msg.content)}
                    className="absolute top-2 right-2 p-1.5 opacity-0 group-hover:opacity-100 bg-slate-800/50 hover:bg-slate-700 rounded-md transition-all text-slate-400 hover:text-white"
                    title="Copier"
                  >
                    <Copy size={14} />
                  </button>
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              )}

              {/* Conformity Checks */}
              {msg.conformity && msg.conformity.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-700/50 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                    <ShieldAlert size={12} /> Vérification Conformité
                  </p>
                  {msg.conformity.map((check, i) => (
                    <div key={i} className={`flex items-start gap-2 text-xs p-2 rounded-lg ${
                      check.status === 'conforme' ? 'bg-green-500/10 text-green-400' :
                      check.status === 'non-conforme' ? 'bg-red-500/10 text-red-400' :
                      'bg-amber-500/10 text-amber-400'
                    }`}>
                      {check.status === 'conforme' ? <CheckCircle2 size={14} className="shrink-0 mt-0.5" /> :
                       check.status === 'non-conforme' ? <AlertTriangle size={14} className="shrink-0 mt-0.5" /> :
                       <Clock size={14} className="shrink-0 mt-0.5" />}
                      <div>
                        <span className="font-semibold">{check.norm_reference}</span>
                        <span className="text-slate-400 ml-2">{check.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Verified Claims (Anti-Hallucination) */}
              {msg.verified_claims && msg.verified_claims.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-700/50 space-y-2">
                  <p className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                    <ShieldAlert size={12} /> Vérification des Affirmations (Anti-Hallucination)
                  </p>
                  {msg.verified_claims.map((claim, i) => (
                    <div key={i} className={`flex items-start gap-2 text-xs p-2 rounded-lg ${
                      claim.status === 'SUPPORTED' ? 'bg-green-500/10 text-green-400' :
                      claim.status === 'UNSUPPORTED' ? 'bg-red-500/10 text-red-400' :
                      'bg-amber-500/10 text-amber-400'
                    }`}>
                      {claim.status === 'SUPPORTED' ? <CheckCircle2 size={14} className="shrink-0 mt-0.5" /> :
                       claim.status === 'UNSUPPORTED' ? <AlertTriangle size={14} className="shrink-0 mt-0.5" /> :
                       <Clock size={14} className="shrink-0 mt-0.5" />}
                      <div>
                        <span className="font-semibold">{claim.statement}</span>
                        {claim.status !== 'SUPPORTED' && <p className="text-slate-400 mt-1">{claim.explanation}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-700/50">
                  <p className="text-xs font-semibold text-slate-400 mb-2 flex items-center gap-1">
                    <Paperclip size={12} /> Sources certifiées
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {msg.sources.map((source, i) => (
                      <span key={i} className="badge badge-cyan text-[11px]">
                        <FileText size={10} />
                        {source.document_name}
                        {source.page_number && ` p.${source.page_number}`}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Processing time & Confidence */}
              {msg.processing_time_ms && (
                <div className="mt-3 flex items-center gap-3">
                  <p className="text-[10px] text-slate-600 flex items-center gap-1">
                    <Clock size={10} /> {(msg.processing_time_ms / 1000).toFixed(1)}s • Agent: {msg.agent_used}
                  </p>
                  {msg.confidence !== undefined && (
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      msg.confidence >= 80 ? 'bg-green-500/20 text-green-400' :
                      msg.confidence >= 50 ? 'bg-amber-500/20 text-amber-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      Confiance : {msg.confidence}%
                    </span>
                  )}
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-9 h-9 rounded-xl bg-slate-700 flex items-center justify-center shrink-0">
                <User size={18} className="text-slate-300" />
              </div>
            )}
          </div>
        ))}

        {/* Typing Indicator */}
        {isLoading && (
          <div className="flex gap-4 fade-in">
            <div className="w-9 h-9 rounded-xl gradient-brand flex items-center justify-center shrink-0 glow-green">
              <Bot size={18} className="text-white" />
            </div>
            <div className="chat-bubble-bot p-5 flex items-center gap-3">
              <div className="flex gap-1.5">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
              <span className="text-xs text-slate-500 italic">Interrogation de la base vectorielle BTP...</span>
            </div>
          </div>
        )}

        {/* Quick Questions */}
        {messages.length <= 1 && (
          <div className="mt-6 space-y-2">
            <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Questions suggérées</p>
            <div className="flex flex-wrap gap-2">
              {quickQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInput(q)}
                  className="text-sm text-slate-400 bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700 px-4 py-2.5 rounded-xl transition-all hover:text-white hover:border-btpGreen/30"
                >
                  <ChevronRight size={14} className="inline mr-1 text-btpGreen" />
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-800 bg-surface-secondary/30 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text"
            className="input-dark w-full pl-5 pr-14 py-4 rounded-2xl"
            placeholder="Ex: Quelles sont les obligations du DTU 20.1 pour un mur de soutènement ?"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="absolute right-2 btn-primary p-3 rounded-xl"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-center mt-2 text-[11px] text-slate-600">
          E-MPGT IA · Réponses sourcées via Qdrant + Neo4j · Agent Conformité DTU actif
        </p>
      </div>
    </div>
  );
}
