import React, { useState, useEffect } from 'react';
import {
  Incident,
  Asset,
  Evidence,
  AssetRelationship,
} from '../../types';
import { FindingBadge } from '../common/FindingBadge';
import { EvidenceBadge } from '../common/EvidenceBadge';
import { graphService, GraphResponseData } from '../../services/graphService';
import {
  Network,
  Cpu,
  FileSpreadsheet,
  AlertTriangle,
  Info,
  X,
  ExternalLink,
  Layers,
  Filter,
  Eye,
  CheckCircle2,
} from 'lucide-react';

interface ContextGraphViewProps {
  incident: Incident;
  assets: Asset[];
  relationships: AssetRelationship[];
  evidenceList: Evidence[];
  onSelectEvidence: (evidence: Evidence) => void;
}

interface GraphNode {
  id: string;
  name: string;
  type: 'incident' | 'asset' | 'evidence';
  x: number;
  y: number;
  data: any;
  color: string;
  borderColor: string;
}

interface GraphLink {
  id: string;
  source: string;
  target: string;
  label: string;
  type: 'incident_asset' | 'asset_asset' | 'evidence_asset';
}

export const ContextGraphView: React.FC<ContextGraphViewProps> = ({
  incident,
  assets,
  relationships,
  evidenceList,
  onSelectEvidence,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string>('P-204');
  const [filterType, setFilterType] = useState<'all' | 'assets' | 'evidence'>('all');
  const [graphSource, setGraphSource] = useState<'LIVE' | 'MOCK'>('MOCK');
  const [activeGraphData, setActiveGraphData] = useState<{
    nodes: GraphNode[];
    links: GraphLink[];
  } | null>(null);

  // Define fallback layout coordinates for SVG canvas (1000 x 600)
  const defaultNodes: GraphNode[] = [
    // Central Incident Node
    {
      id: incident.id,
      name: incident.id,
      type: 'incident',
      x: 500,
      y: 280,
      data: incident,
      color: '#0f172a',
      borderColor: '#38bdf8',
    },
    // 4 Asset Nodes (Arranged logically horizontally/elliptically)
    {
      id: 'VFD-204',
      name: 'VFD-204',
      type: 'asset',
      x: 230,
      y: 200,
      data: assets.find((a) => a.id === 'VFD-204'),
      color: '#1e1b4b',
      borderColor: '#818cf8',
    },
    {
      id: 'M-204',
      name: 'Motor M-204',
      type: 'asset',
      x: 410,
      y: 130,
      data: assets.find((a) => a.id === 'M-204'),
      color: '#1e1b4b',
      borderColor: '#60a5fa',
    },
    {
      id: 'P-204',
      name: 'Pump P-204',
      type: 'asset',
      x: 590,
      y: 130,
      data: assets.find((a) => a.id === 'P-204'),
      color: '#4c0519',
      borderColor: '#f43f5e',
    },
    {
      id: 'PLC-204',
      name: 'PLC-204',
      type: 'asset',
      x: 770,
      y: 200,
      data: assets.find((a) => a.id === 'PLC-204'),
      color: '#064e3b',
      borderColor: '#34d399',
    },
    // 6 Evidence Nodes (Outer Orbit)
    {
      id: 'EVD-001',
      name: 'VFD_204_Log.csv',
      type: 'evidence',
      x: 140,
      y: 350,
      data: evidenceList.find((e) => e.id === 'EVD-001'),
      color: '#082f49',
      borderColor: '#38bdf8',
    },
    {
      id: 'EVD-005',
      name: 'Maintenance_M204_Report.pdf',
      type: 'evidence',
      x: 350,
      y: 430,
      data: evidenceList.find((e) => e.id === 'EVD-005'),
      color: '#451a03',
      borderColor: '#fbbf24',
    },
    {
      id: 'EVD-003',
      name: 'Historian_P204.csv',
      type: 'evidence',
      x: 500,
      y: 470,
      data: evidenceList.find((e) => e.id === 'EVD-003'),
      color: '#022c22',
      borderColor: '#4ade80',
    },
    {
      id: 'EVD-004',
      name: 'Pump_P204_Manual.pdf',
      type: 'evidence',
      x: 670,
      y: 430,
      data: evidenceList.find((e) => e.id === 'EVD-004'),
      color: '#3b0764',
      borderColor: '#c084fc',
    },
    {
      id: 'EVD-006',
      name: 'Technician_Observation_001',
      type: 'evidence',
      x: 840,
      y: 350,
      data: evidenceList.find((e) => e.id === 'EVD-006'),
      color: '#4c0519',
      borderColor: '#fb7185',
    },
    {
      id: 'EVD-002',
      name: 'SCADA_Alarm_Log.csv',
      type: 'evidence',
      x: 870,
      y: 110,
      data: evidenceList.find((e) => e.id === 'EVD-002'),
      color: '#083344',
      borderColor: '#22d3ee',
    },
  ];

  // Semantic Edges fallback
  const defaultLinks: GraphLink[] = [
    // Incident connects to assets
    { id: 'L1', source: incident.id, target: 'VFD-204', label: 'originates at', type: 'incident_asset' },
    { id: 'L2', source: incident.id, target: 'M-204', label: 'involves', type: 'incident_asset' },
    { id: 'L3', source: incident.id, target: 'P-204', label: 'primary target', type: 'incident_asset' },
    { id: 'L4', source: incident.id, target: 'PLC-204', label: 'interlock trip', type: 'incident_asset' },

    // Asset physical couplings
    { id: 'L5', source: 'VFD-204', target: 'M-204', label: 'powers', type: 'asset_asset' },
    { id: 'L6', source: 'M-204', target: 'P-204', label: 'drives', type: 'asset_asset' },
    { id: 'L7', source: 'P-204', target: 'PLC-204', label: 'monitored by', type: 'asset_asset' },

    // Evidence connections
    { id: 'L8', source: 'EVD-001', target: 'VFD-204', label: 'logged in', type: 'evidence_asset' },
    { id: 'L9', source: 'EVD-005', target: 'M-204', label: 'maintenance', type: 'evidence_asset' },
    { id: 'L10', source: 'EVD-003', target: 'P-204', label: 'telemetry', type: 'evidence_asset' },
    { id: 'L11', source: 'EVD-004', target: 'P-204', label: 'manual limits', type: 'evidence_asset' },
    { id: 'L12', source: 'EVD-006', target: 'P-204', label: 'witness note', type: 'evidence_asset' },
    { id: 'L13', source: 'EVD-002', target: 'PLC-204', label: 'trip sequence', type: 'evidence_asset' },
  ];

  // Fetch live incident context graph from backend endpoint
  useEffect(() => {
    let isMounted = true;

    async function loadGraph() {
      try {
        const res = await graphService.getIncidentGraph(incident.id);
        if (!isMounted) return;

        if (res && Array.isArray(res.nodes) && res.nodes.length > 0) {
          const mappedNodes: GraphNode[] = res.nodes.map((node, index) => {
            const defaultMatch = defaultNodes.find((dn) => dn.id === node.id);
            if (defaultMatch) {
              return {
                ...defaultMatch,
                name: node.label || defaultMatch.name,
              };
            }

            const angle = (index / res.nodes.length) * 2 * Math.PI;
            const cx = 500;
            const cy = 280;
            const rx = 370;
            const ry = 210;
            const nx = Math.round(cx + rx * Math.cos(angle));
            const ny = Math.round(cy + ry * Math.sin(angle));

            const isAsset = node.type?.toLowerCase() === 'asset';
            const isEvidence = node.type?.toLowerCase() === 'evidence';

            const nodeType: 'incident' | 'asset' | 'evidence' = isAsset
              ? 'asset'
              : isEvidence
              ? 'evidence'
              : 'incident';

            const matchingAsset = assets.find((a) => a.id === node.id);
            const matchingEvidence = evidenceList.find((e) => e.id === node.id);

            return {
              id: node.id,
              name: node.label || node.id,
              type: nodeType,
              x: Math.max(90, Math.min(910, nx)),
              y: Math.max(90, Math.min(510, ny)),
              data: matchingAsset || matchingEvidence || node.metadata || {},
              color: isAsset ? '#1e1b4b' : isEvidence ? '#082f49' : '#0f172a',
              borderColor: isAsset ? '#818cf8' : isEvidence ? '#38bdf8' : '#38bdf8',
            };
          });

          const mappedLinks: GraphLink[] = (res.edges || []).map((edge, idx) => {
            const sNode = res.nodes.find((n) => n.id === edge.source);
            const tNode = res.nodes.find((n) => n.id === edge.target);

            const isAssetLink =
              sNode?.type?.toLowerCase() === 'asset' &&
              tNode?.type?.toLowerCase() === 'asset';
            const isIncidentLink =
              sNode?.type?.toLowerCase() === 'incident' ||
              tNode?.type?.toLowerCase() === 'incident';

            return {
              id: edge.id || `L-live-${idx}`,
              source: edge.source,
              target: edge.target,
              label: (edge.relationship || 'rel').toLowerCase().replace(/_/g, ' '),
              type: isAssetLink
                ? 'asset_asset'
                : isIncidentLink
                ? 'incident_asset'
                : 'evidence_asset',
            };
          });

          setActiveGraphData({ nodes: mappedNodes, links: mappedLinks });
          setGraphSource(res.source === 'neo4j' ? 'LIVE' : 'MOCK');
        } else {
          setGraphSource('MOCK');
          setActiveGraphData(null);
        }
      } catch {
        if (isMounted) {
          setGraphSource('MOCK');
          setActiveGraphData(null);
        }
      }
    }

    loadGraph();
    return () => {
      isMounted = false;
    };
  }, [incident.id]);

  const nodes = activeGraphData?.nodes || defaultNodes;
  const links = activeGraphData?.links || defaultLinks;

  // Selected node object
  const activeNode = nodes.find((n) => n.id === selectedNodeId) || nodes[0];

  // Filter nodes & links
  const visibleNodes = nodes.filter((n) => {
    if (filterType === 'assets') return n.type === 'incident' || n.type === 'asset';
    if (filterType === 'evidence') return n.type === 'incident' || n.type === 'evidence';
    return true;
  });

  const isLinkVisible = (link: GraphLink) => {
    const sVis = visibleNodes.some((n) => n.id === link.source);
    const tVis = visibleNodes.some((n) => n.id === link.target);
    return sVis && tVis;
  };

  return (
    <div id="context-graph-view" className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono uppercase tracking-widest text-cyan-400">
              Multimodal Knowledge & Topology
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-purple-950 border border-purple-800 text-purple-300 font-mono">
              Incident Context Graph
            </span>
          </div>
          <h1 className="text-2xl font-bold font-mono text-white mt-1">
            Incident Topology & Evidence Graph
          </h1>
          <p className="text-xs text-slate-400 font-sans">
            Interactive node-link model connecting Incident INC-2026-001, physical assets, and multimodal evidence.
          </p>
        </div>

        {/* Graph Status Indicator & Filter Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                graphSource === 'LIVE' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span className="text-slate-400 text-[11px]">GRAPH:</span>
            <span
              className={`font-bold text-[11px] tracking-wider ${
                graphSource === 'LIVE' ? 'text-emerald-400' : 'text-amber-400'
              }`}
            >
              {graphSource}
            </span>
          </div>

          {/* Filter Buttons */}
          <div className="flex items-center gap-1.5 p-1 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs">
          <button
            onClick={() => setFilterType('all')}
            className={`px-3 py-1 rounded transition-colors ${
              filterType === 'all'
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All Entities ({nodes.length})
          </button>
          <button
            onClick={() => setFilterType('assets')}
            className={`px-3 py-1 rounded transition-colors ${
              filterType === 'assets'
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Assets Only
          </button>
          <button
            onClick={() => setFilterType('evidence')}
            className={`px-3 py-1 rounded transition-colors ${
              filterType === 'evidence'
                ? 'bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Evidence Only
          </button>
        </div>
        </div>
      </div>

      {/* Main Graph Grid (SVG Canvas + Side Inspector Panel) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SVG Graph Canvas (8 Cols) */}
        <div className="lg:col-span-8 rounded-xl border border-slate-800 bg-[#070b14] p-4 relative overflow-hidden shadow-2xl bg-grid-scada">
          {/* Canvas Legend */}
          <div className="absolute top-4 left-4 flex flex-wrap items-center gap-3 text-[11px] font-mono text-slate-400 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800/80 z-10 backdrop-blur-sm">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400" /> Incident
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" /> Asset
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Evidence
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-500">Click any node to inspect</span>
          </div>

          <svg
            viewBox="0 0 1000 580"
            className="w-full h-auto min-h-[460px] select-none"
          >
            <defs>
              <linearGradient id="linkGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#818cf8" stopOpacity="0.2" />
              </linearGradient>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="6"
                refX="7"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
              </marker>
            </defs>

            {/* Render Links */}
            {links.map((link) => {
              if (!isLinkVisible(link)) return null;
              const sourceNode = nodes.find((n) => n.id === link.source);
              const targetNode = nodes.find((n) => n.id === link.target);
              if (!sourceNode || !targetNode) return null;

              const isHighlighted =
                selectedNodeId === link.source || selectedNodeId === link.target;

              const midX = (sourceNode.x + targetNode.x) / 2;
              const midY = (sourceNode.y + targetNode.y) / 2;

              return (
                <g key={link.id} className="transition-all duration-300">
                  <line
                    x1={sourceNode.x}
                    y1={sourceNode.y}
                    x2={targetNode.x}
                    y2={targetNode.y}
                    stroke={
                      isHighlighted
                        ? '#38bdf8'
                        : link.type === 'asset_asset'
                        ? '#3b82f6'
                        : '#334155'
                    }
                    strokeWidth={isHighlighted ? 2.5 : link.type === 'asset_asset' ? 2 : 1.2}
                    strokeDasharray={link.type === 'evidence_asset' ? '4 3' : 'none'}
                    markerEnd="url(#arrowhead)"
                  />
                  {/* Link semantic label */}
                  <text
                    x={midX}
                    y={midY - 4}
                    fill={isHighlighted ? '#7dd3fc' : '#64748b'}
                    fontSize="10"
                    fontFamily="monospace"
                    textAnchor="middle"
                    className="select-none pointer-events-none"
                  >
                    {link.label}
                  </text>
                </g>
              );
            })}

            {/* Render Nodes */}
            {visibleNodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const isIncident = node.type === 'incident';
              const isAsset = node.type === 'asset';

              const r = isIncident ? 42 : isAsset ? 34 : 26;

              return (
                <g
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  className="cursor-pointer transition-all duration-200 group"
                >
                  {/* Outer pulse circle if selected */}
                  {isSelected && (
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={r + 8}
                      fill="none"
                      stroke={node.borderColor}
                      strokeWidth="2"
                      strokeDasharray="4 2"
                      className="animate-spin"
                      style={{ transformOrigin: `${node.x}px ${node.y}px`, animationDuration: '8s' }}
                    />
                  )}

                  {/* Base Circle */}
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={r}
                    fill={node.color}
                    stroke={node.borderColor}
                    strokeWidth={isSelected ? 3 : 1.8}
                    className="group-hover:scale-105 transition-transform"
                  />

                  {/* Icon or Monogram */}
                  <text
                    x={node.x}
                    y={node.y - (isIncident ? 8 : 4)}
                    fill="#f8fafc"
                    fontSize={isIncident ? '12' : '11'}
                    fontFamily="monospace"
                    fontWeight="bold"
                    textAnchor="middle"
                    className="pointer-events-none"
                  >
                    {node.name.length > 14 ? node.name.slice(0, 12) + '…' : node.name}
                  </text>

                  <text
                    x={node.x}
                    y={node.y + (isIncident ? 14 : 12)}
                    fill={isIncident ? '#38bdf8' : isAsset ? '#a5b4fc' : '#86efac'}
                    fontSize="9"
                    fontFamily="monospace"
                    textAnchor="middle"
                    className="pointer-events-none uppercase tracking-wider"
                  >
                    {node.type}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Node Information Inspector Panel (4 Cols) */}
        <div className="lg:col-span-4 rounded-xl border border-slate-800 bg-[#0a0f1d] p-5 flex flex-col justify-between shadow-xl space-y-4">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-white">
                  Node Inspector
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 uppercase">
                {activeNode.type}
              </span>
            </div>

            {/* Selected Node Details */}
            <div className="mt-4 space-y-4 font-mono text-xs">
              <div>
                <span className="text-slate-500 block text-[10px] uppercase">Selected Identifier</span>
                <div className="text-base font-bold text-white mt-0.5">
                  {activeNode.name}
                </div>
              </div>

              {/* Node-type specific inspection body */}
              {activeNode.type === 'asset' && activeNode.data && (
                <div className="space-y-3">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Classification</span>
                    <span className="text-cyan-300">{activeNode.data.type}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Location</span>
                    <span className="text-slate-300">{activeNode.data.plantArea}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Operational State</span>
                    <span
                      className={`inline-block px-2 py-0.5 rounded font-bold mt-1 ${
                        activeNode.data.status === 'Tripped'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : activeNode.data.status === 'Warning'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      }`}
                    >
                      {activeNode.data.status}
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-black/40 border border-slate-800 space-y-1.5">
                    <span className="text-[10px] text-slate-500 uppercase block font-bold">Specs</span>
                    {Object.entries(activeNode.data.specs || {}).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-[11px]">
                        <span className="text-slate-500">{k}:</span>
                        <span className="text-slate-200">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeNode.type === 'evidence' && activeNode.data && (
                <div className="space-y-3">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Evidence Category</span>
                    <div className="mt-1">
                      <EvidenceBadge category={activeNode.data.sourceType} size="sm" />
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Associated Asset</span>
                    <span className="text-cyan-300 font-bold">{activeNode.data.assetId}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Normalized Timestamp</span>
                    <span className="text-slate-300">{activeNode.data.normalizedTimestamp}</span>
                  </div>
                  <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/40">
                    <span className="text-[10px] text-cyan-400 uppercase font-bold block mb-1">
                      Extracted Event
                    </span>
                    <p className="text-[11px] text-cyan-100 font-sans leading-relaxed">
                      {activeNode.data.extractedEvent}
                    </p>
                  </div>
                  <button
                    onClick={() => onSelectEvidence(activeNode.data)}
                    className="w-full py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
                  >
                    <span>Inspect Raw Artifact</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              {activeNode.type === 'incident' && (
                <div className="space-y-3">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Plant Area</span>
                    <span className="text-slate-200">{incident.plantArea}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase">Severity & Status</span>
                    <span className="text-rose-400 font-bold">{incident.severity}</span> •{' '}
                    <span className="text-amber-400">{incident.status}</span>
                  </div>
                  <p className="text-xs text-slate-300 font-sans leading-relaxed">
                    {incident.summary}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 text-[10px] font-mono text-slate-500">
            Graph Topology: {nodes.length} Nodes • {links.length} Relations
          </div>
        </div>
      </div>
    </div>
  );
};
