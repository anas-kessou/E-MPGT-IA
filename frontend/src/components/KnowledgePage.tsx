import React, { useState, useEffect, useRef } from 'react';
import { Share2, RotateCcw, Database, Info, Maximize2, ZoomIn, ZoomOut } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import { getKnowledgeOverview, getLatestGraphData, getGraphData } from '../api/client';
import { GraphOverview } from '../types';

export function KnowledgePage() {
  const [overview, setOverview] = useState<GraphOverview | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const fgRef = useRef<any>();

  useEffect(() => {
    async function init() {
      try {
        const [ov, gd] = await Promise.all([
          getKnowledgeOverview(),
          getLatestGraphData(40)
        ]);
        setOverview(ov);
        
        // Transform Neo4j data to ForceGraph format
        const nodes = gd.nodes.map((n: any) => ({
          ...n,
          name: n.properties.filename || n.properties.reference || n.properties.name || n.properties.id || 'Node',
          val: n.labels[0] === 'Document' ? 5 : 3
        }));
        
        const links = gd.edges.map((e: any) => ({
          id: e.id,
          source: e.start,
          target: e.end,
          label: e.type
        }));
        
        setGraphData({ nodes, links });
      } catch (err) {
        console.error("Failed to load graph:", err);
        // Fallback for demo
        setOverview({
          nodes: { Document: 33, Projet: 3, Norme: 12, Lot: 8, Fournisseur: 5 },
          relationships: { APPARTIENT_A: 28, REFERENCE: 45, CONCERNE: 22, FOURNIT: 8 },
        });
      }
      setLoading(false);
    }
    init();
  }, []);

  const handleNodeClick = async (node: any) => {
    setSelectedNode(node);
    fgRef.current.centerAt(node.x, node.y, 400);
    fgRef.current.zoom(3, 400);

    // Expand graph around this node
    try {
      const moreData = await getGraphData(node.properties.id, node.labels[0]);
      
      const newNodes = [...graphData.nodes];
      const newLinks = [...graphData.links];
      
      moreData.nodes.forEach((n: any) => {
        if (!newNodes.find(en => en.id === n.id)) {
          newNodes.push({
            ...n,
            name: n.properties.filename || n.properties.reference || n.properties.name || n.properties.id || 'Node',
            val: n.labels[0] === 'Document' ? 5 : 3
          });
        }
      });
      
      moreData.edges.forEach((e: any) => {
        if (!newLinks.find(el => el.id === e.id)) {
          newLinks.push({
            id: e.id,
            source: e.start,
            target: e.end,
            label: e.type
          });
        }
      });
      
      setGraphData({ nodes: newNodes, links: newLinks });
    } catch (e) {
      console.warn("Could not expand node", e);
    }
  };

  const nodeColors: Record<string, string> = {
    Document: '#06b6d4',
    Projet: '#10b981',
    Norme: '#f59e0b',
    Lot: '#a855f7',
    Fournisseur: '#ec4899',
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-950">
      {/* Overlay Header */}
      <div className="absolute top-0 left-0 right-0 p-6 z-10 pointer-events-none">
        <div className="flex items-center justify-between pointer-events-auto">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="p-2 bg-btpGreen/10 rounded-lg text-btpGreen">
                <Share2 size={24} />
              </span>
              Knowledge Graph
            </h2>
            <p className="text-slate-400 mt-1">Exploration interactive des relations techniques BTP</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={() => {
                setGraphData({ nodes: [], links: [] });
                setSelectedNode(null);
                // Trigger reload
                window.location.reload();
              }}
              className="bg-slate-900/80 backdrop-blur-md border border-slate-800 p-2.5 rounded-xl text-slate-400 hover:text-white hover:border-btpGreen/50 transition-all shadow-xl"
              title="Reset View"
            >
              <RotateCcw size={20} />
            </button>
            <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 p-1 rounded-xl flex items-center shadow-xl">
              <button 
                onClick={() => fgRef.current.zoom(fgRef.current.zoom() * 1.5, 400)}
                className="p-2 text-slate-400 hover:text-white transition-colors"
                title="Zoom In"
              >
                <ZoomIn size={18} />
              </button>
              <div className="w-[1px] h-4 bg-slate-800" />
              <button 
                onClick={() => fgRef.current.zoom(fgRef.current.zoom() * 0.7, 400)}
                className="p-2 text-slate-400 hover:text-white transition-colors"
                title="Zoom Out"
              >
                <ZoomOut size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Stats Row */}
        {overview && (
          <div className="mt-6 flex flex-wrap gap-3 pointer-events-auto">
            {Object.entries(overview.nodes).map(([type, count]) => (
              <div key={type} className="bg-slate-900/60 backdrop-blur-sm border border-slate-800/50 px-3 py-1.5 rounded-full flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: nodeColors[type] || '#64748b' }} />
                <span className="text-xs font-bold text-white">{count}</span>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">{type}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Graph Area */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Database className="w-10 h-10 text-btpGreen animate-pulse mx-auto mb-4" />
              <p className="text-slate-400">Interrogation de Neo4j...</p>
            </div>
          </div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            nodeLabel={(node: any) => `
              <div class="bg-slate-900 border border-slate-700 p-2 rounded-lg shadow-2xl">
                <p class="text-xs font-bold text-white mb-1">${node.labels[0]}</p>
                <p class="text-[11px] text-slate-400">${node.name}</p>
              </div>
            `}
            nodeColor={(node: any) => nodeColors[node.labels[0]] || '#64748b'}
            nodeRelSize={6}
            linkColor={() => '#1e293b'}
            linkWidth={1.5}
            linkDirectionalParticles={2}
            linkDirectionalParticleSpeed={0.005}
            onNodeClick={handleNodeClick}
            backgroundColor="#020617"
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              const label = node.name;
              const fontSize = 12/globalScale;
              ctx.font = `${fontSize}px Inter, sans-serif`;
              
              // Draw circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
              ctx.fillStyle = nodeColors[node.labels[0]] || '#64748b';
              ctx.fill();
              
              // Add outline to selected
              if (selectedNode?.id === node.id) {
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2/globalScale;
                ctx.stroke();
              }

              // Text label
              if (globalScale > 1.5) {
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                ctx.fillStyle = '#94a3b8';
                ctx.fillText(label, node.x, node.y + 8);
              }
            }}
          />
        )}
      </div>

      {/* Detail Panel */}
      {selectedNode && (
        <div className="absolute bottom-6 right-6 w-80 bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-2xl p-5 shadow-2xl animate-in slide-in-from-right-10 duration-300">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Info size={14} className="text-btpGreen" />
              Détails du Nœud
            </h3>
            <button 
              onClick={() => setSelectedNode(null)}
              className="text-slate-500 hover:text-white"
            >
              <Maximize2 size={16} />
            </button>
          </div>
          
          <div className="space-y-4">
            <div className={`p-4 rounded-xl border border-BTG opacity-85`} style={{ borderColor: nodeColors[selectedNode.labels[0]] + '33', backgroundColor: nodeColors[selectedNode.labels[0]] + '11' }}>
              <p className="text-[10px] text-slate-500 uppercase font-bold mb-1">{selectedNode.labels[0]}</p>
              <p className="text-sm font-bold text-white break-words">{selectedNode.name}</p>
            </div>
            
            <div className="space-y-2">
              {Object.entries(selectedNode.properties).map(([key, val]) => (
                <div key={key} className="flex justify-between border-b border-slate-800/50 pb-1.5 last:border-0">
                  <span className="text-[11px] text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="text-[11px] text-slate-300 font-medium truncate max-w-[140px]" title={String(val)}>
                    {String(val)}
                  </span>
                </div>
              ))}
            </div>
            
            <button 
              className="w-full bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold py-2.5 rounded-xl transition-all"
              onClick={() => handleNodeClick(selectedNode)}
            >
              Explorer les connexions
            </button>
          </div>
        </div>
      )}

      {/* Legend / Instructions */}
      <div className="absolute bottom-6 left-6 p-4 bg-slate-900/60 backdrop-blur-md border border-slate-800/50 rounded-2xl flex items-center gap-6 pointer-events-none">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-btpGreen rounded-full" />
          <span className="text-[10px] text-slate-400 font-medium tracking-tight">Clic pour recentrer</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-btpCyan rounded-full" />
          <span className="text-[10px] text-slate-400 font-medium tracking-tight">Double-clic pour explorer</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-slate-500 rounded-full" />
          <span className="text-[10px] text-slate-400 font-medium tracking-tight">Drag pour déplacer</span>
        </div>
      </div>
    </div>
  );
}
