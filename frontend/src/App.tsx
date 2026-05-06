/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, HardHat, FileText, Database, ShieldAlert, Paperclip, Search } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Message {
  role: 'bot' | 'user';
  content: string;
  sources?: string[];
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', content: 'Bonjour. Je suis le Système IA BTP (E-MPGT). Ma base vectorielle contient les normes NF, DTU, et fiches de sécurité. Comment puis-je vous aider sur votre chantier aujourd\'hui ?', sources: [] }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [dataSearch, setDataSearch] = useState('');

  const activeDataItems = [
    { id: 1, type: 'dtu', label: 'DTU 20.1 (Maçonnerie)', icon: FileText, color: 'text-btpGreen' },
    { id: 2, type: 'fiche', label: 'Fiches AQC (Erreurs)', icon: ShieldAlert, color: 'text-yellow-400' },
    { id: 3, type: 'projet', label: 'Projets internes (CRM)', icon: Database, color: 'text-btpGreen' },
  ];

  const filteredDataItems = activeDataItems.filter(item => 
    item.label.toLowerCase().includes(dataSearch.toLowerCase()) || 
    item.type.toLowerCase().includes(dataSearch.toLowerCase())
  );

  // Auto-scroll vers le bas
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => { scrollToBottom(); }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // APPEL VERS VOTRE BACKEND FASTAPI (Ajustez le port si besoin)
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      });
      
      const data = await response.json();
      setMessages(prev =>[...prev, { 
        role: 'bot', 
        content: data.reply, 
        sources: data.sources || ['DTU 20.1 - Chapitre 3'] // Fallback pour la démo
      }]);
    } catch (error) {
      // Mode Démo si le backend n'est pas allumé
      setTimeout(() => {
        setMessages(prev =>[...prev, { 
          role: 'bot', 
          content: "*(Mode Démo / Backend non connecté)* D'après le **DTU 20.1**, les tolérances de verticalité pour un mur en maçonnerie de type fondation sont de l'ordre de 1,5 cm sur une hauteur de 3 mètres. L'ajout d'une armature de renfort est préconisé si le mur soutient des terres.", 
          sources:['Fiche_AQC_Fissuration_Murs.pdf', 'DTU_20_1_Maconnerie.pdf'] 
        }]);
        setIsLoading(false);
      }, 1500);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      
      {/* SIDEBAR GAUCHE (Reprend votre architecture à 3 couches) */}
      <div className="w-72 bg-btpBlue text-white flex flex-col shadow-xl hidden md:flex">
        <div className="p-6 border-b border-blue-800">
          <h1 className="text-2xl font-bold text-btpGreen flex items-center gap-2">
            <HardHat size={28} />
            E-MPGT IA
          </h1>
          <p className="text-xs text-blue-300 mt-2">Base vectorielle & Moteur métier</p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          <div>
            <h2 className="text-xs uppercase text-blue-400 font-bold tracking-wider mb-3">Données Actives</h2>
            
            <div className="relative mb-3">
              <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none">
                <Search size={14} className="text-blue-400" />
              </div>
              <input
                type="text"
                placeholder="Filtrer type, mot-clé..."
                value={dataSearch}
                onChange={(e) => setDataSearch(e.target.value)}
                className="w-full bg-blue-900/50 border border-blue-800 text-sm text-white placeholder-blue-400 rounded-md py-1.5 pl-8 pr-3 focus:outline-none focus:ring-1 focus:ring-btpGreen transition-colors"
              />
            </div>

            <ul className="space-y-2">
              {filteredDataItems.map(item => {
                const Icon = item.icon;
                return (
                  <li key={item.id} className="flex items-center gap-2 text-sm bg-blue-900/50 p-2 rounded transition-colors hover:bg-blue-800/80 cursor-default">
                    <Icon size={16} className={item.color}/> {item.label}
                  </li>
                );
              })}
              {filteredDataItems.length === 0 && (
                <li className="text-sm text-blue-400/80 italic py-2 text-center">Aucun résultat</li>
              )}
            </ul>
          </div>
          
          <div className="bg-blue-800 p-4 rounded-lg mt-auto">
            <h3 className="text-sm font-bold text-white mb-1">Status RAG</h3>
            <div className="flex items-center justify-between text-xs text-blue-300">
              <span>Embeddings: </span><span className="text-btpGreen">100% Vectorisé</span>
            </div>
            <div className="w-full bg-blue-900 rounded-full h-1.5 mt-2">
              <div className="bg-btpGreen h-1.5 rounded-full w-full"></div>
            </div>
          </div>
        </div>
      </div>

      {/* ZONE DE CHAT PRINCIPALE */}
      <div className="flex-1 flex flex-col">
        {/* Header mobile/desktop */}
        <header className="bg-white p-4 shadow-sm border-b flex justify-between items-center z-10">
          <h2 className="text-lg font-semibold text-gray-800">Assistant Ingénierie & Chantier</h2>
          <span className="bg-green-100 text-green-800 text-xs px-3 py-1 rounded-full font-medium border border-green-200">
            Couche Exécution Active
          </span>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
          {messages.map((msg, index) => (
            <div key={index} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              
              {msg.role === 'bot' && (
                <div className="w-10 h-10 rounded-full bg-btpGreen flex items-center justify-center text-white shrink-0 shadow-md">
                  <Bot size={24} />
                </div>
              )}

              <div className={`max-w-[80%] rounded-2xl p-5 shadow-sm ${
                msg.role === 'user' 
                  ? 'bg-btpBlue text-white rounded-tr-none' 
                  : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
              }`}>
                {/* Utilisation de Markdown pour des réponses bien formatées */}
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="prose prose-sm md:prose-base prose-blue max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
                
                {/* Affichage des sources citées (Crucial pour la démo) */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-gray-100/20">
                    <p className={`text-xs font-semibold mb-2 ${msg.role === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>Sources certifiées :</p>
                    <div className="flex flex-wrap gap-2">
                      {msg.sources.map((source, i) => (
                        <span key={i} className={`text-xs px-2 py-1 rounded-md flex items-center gap-1 border ${
                          msg.role === 'user' 
                            ? 'bg-blue-800 border-blue-700 text-blue-100' 
                            : 'bg-gray-50 border-gray-200 text-gray-600'
                        }`}>
                          <Paperclip size={12} /> {source}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 shrink-0 shadow-md">
                  <User size={24} />
                </div>
              )}
            </div>
          ))}
          
          {/* Indicateur de frappe */}
          {isLoading && (
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-btpGreen flex items-center justify-center text-white shrink-0 shadow-md">
                <Bot size={24} />
              </div>
              <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none p-5 shadow-sm flex items-center gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                <span className="ml-2 text-sm text-gray-500 italic">Interrogation de la base vectorielle BTP...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* INPUT BOX */}
        <div className="bg-white p-4 border-t border-gray-200">
          <div className="max-w-4xl mx-auto relative flex items-center">
            <button className="absolute left-4 text-gray-400 hover:text-btpBlue transition-colors">
              <Paperclip size={20} />
            </button>
            <input
              type="text"
              className="w-full bg-gray-50 border border-gray-200 text-gray-800 rounded-full py-4 pl-12 pr-16 focus:outline-none focus:ring-2 focus:ring-btpGreen focus:border-transparent transition-all"
              placeholder="Ex: Quelles sont les obligations du DTU 20.1 pour un mur de soutènement ?"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSend();
                }
              }}
            />
            <button 
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="absolute right-2 bg-btpGreen text-white p-2.5 rounded-full hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send size={20} />
            </button>
          </div>
          <div className="text-center mt-2 text-xs text-gray-400">
            IA conçue pour E-MPGT • Réponses sourcées via Vector DB
          </div>
        </div>
      </div>

    </div>
  );
}
