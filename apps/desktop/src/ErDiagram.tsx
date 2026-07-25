import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background, Controls, Handle, MarkerType, MiniMap, Position, ReactFlow,
  ReactFlowProvider, useEdgesState, useNodesState, useReactFlow,
  type Edge, type Node, type NodeProps,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import { toPng } from "html-to-image";
import { Columns3, Download, KeyRound, Maximize2, Search, Table2 } from "lucide-react";
import "@xyflow/react/dist/style.css";

export type ErColumn = {
  column_name: string; data_type: string; nullable: boolean;
  primary_key: boolean; protected: boolean;
};
export type ErRelation = {
  column_name: string; target_schema: string; target_table: string;
  target_column: string; constraint_name: string;
};
export type ErObject = {
  object_name: string; object_type: string; columns: ErColumn[]; relations: ErRelation[];
};
export type ErSchema = { name: string; objects: ErObject[] };
export type ErScope =
  | { kind: "schema"; schema: string }
  | { kind: "table"; schema: string; table: string }
  | { kind: "query"; label: string; sql: string };
export type ErLabels = {
  findTable: string; columns: string; horizontal: string; vertical: string;
  fit: string; noTables: string; noTablesHelp: string; tables: string; relations: string;
  table: string; view: string; primaryKey: string; foreignKey: string; notNull: string;
};

type DiagramTable = { id: string; schema: string; object: ErObject };
type QueryJoin = {
  sourceId: string; targetId: string; sourceColumn: string; targetColumn: string; label: string;
};
type TableNodeData = DiagramTable & { foreignKeys: Set<string>; labels: ErLabels };

const NODE_WIDTH = 272;
const NODE_HEADER = 58;
const COLUMN_HEIGHT = 28;

function qualified(schema: string, table: string) {
  return `${schema}.${table}`;
}

function parseQuery(sql: string): { ids: string[]; joins: QueryJoin[] } {
  const identifiers = new Map<string, string>();
  const ids: string[] = [];
  const tablePattern = /\b(from|join)\s+(?:"?([a-z_][\w$]*)"?\.)?"?([a-z_][\w$]*)"?(?:\s+(?:as\s+)?([a-z_][\w$]*))?/gi;
  for (const match of sql.matchAll(tablePattern)) {
    const schema = match[2] || "public";
    const table = match[3];
    const alias = match[4] && !["on", "where", "left", "right", "inner", "full", "join", "order", "group", "limit"].includes(match[4].toLowerCase())
      ? match[4] : table;
    const id = qualified(schema, table);
    if (!ids.includes(id)) ids.push(id);
    identifiers.set(alias, id);
    identifiers.set(table, id);
    identifiers.set(id, id);
  }
  const joins: QueryJoin[] = [];
  const conditionPattern = /\b([a-z_][\w$]*)\.("?[\w$]+"?)\s*=\s*([a-z_][\w$]*)\.("?[\w$]+"?)/gi;
  for (const match of sql.matchAll(conditionPattern)) {
    const sourceId = identifiers.get(match[1]);
    const targetId = identifiers.get(match[3]);
    if (!sourceId || !targetId || sourceId === targetId) continue;
    const sourceColumn = match[2].replace(/"/g, "");
    const targetColumn = match[4].replace(/"/g, "");
    joins.push({
      sourceId, targetId, sourceColumn, targetColumn,
      label: `${sourceColumn} = ${targetColumn}`,
    });
  }
  return { ids, joins };
}

function TableNode({ data, selected }: NodeProps<Node<TableNodeData>>) {
  const visible = data.object.columns.filter((column) => !column.protected);
  return <article className={`er-table-node${selected ? " selected" : ""}`}>
    <Handle type="target" position={Position.Left} />
    <header>
      <Table2 size={16} />
      <div><small>{data.schema}</small><strong>{data.object.object_name}</strong></div>
      <span>{data.object.object_type === "view" ? data.labels.view : data.labels.table}</span>
    </header>
    <div className="er-table-columns">
      {visible.map((column) => <div key={column.column_name}>
        <span className="er-key">
          {column.primary_key ? <KeyRound size={12} aria-label={data.labels.primaryKey} /> :
            data.foreignKeys.has(column.column_name) ? <span title={data.labels.foreignKey}>FK</span> :
              <Columns3 size={11} />}
        </span>
        <strong>{column.column_name}</strong>
        <code>{column.data_type}</code>
        {!column.nullable && <i title={data.labels.notNull}>NN</i>}
      </div>)}
      {!visible.length && <p>No visible columns</p>}
    </div>
    <Handle type="source" position={Position.Right} />
  </article>;
}

const nodeTypes = { table: TableNode };

function layoutElements(tables: DiagramTable[], relations: QueryJoin[], direction: "LR" | "TB", labels: ErLabels) {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: direction, nodesep: 48, ranksep: 105, marginx: 35, marginy: 35 });
  for (const table of tables) {
    const visibleCount = table.object.columns.filter((column) => !column.protected).length;
    graph.setNode(table.id, { width: NODE_WIDTH, height: NODE_HEADER + Math.max(1, visibleCount) * COLUMN_HEIGHT });
  }
  for (const relation of relations) graph.setEdge(relation.sourceId, relation.targetId);
  dagre.layout(graph);

  const foreignByTable = new Map<string, Set<string>>();
  for (const table of tables) {
    foreignByTable.set(table.id, new Set(table.object.relations.map((relation) => relation.column_name)));
  }
  const nodes: Node<TableNodeData>[] = tables.map((table) => {
    const point = graph.node(table.id);
    const visibleCount = table.object.columns.filter((column) => !column.protected).length;
    const height = NODE_HEADER + Math.max(1, visibleCount) * COLUMN_HEIGHT;
    return {
      id: table.id, type: "table",
      position: { x: point.x - NODE_WIDTH / 2, y: point.y - height / 2 },
      data: { ...table, foreignKeys: foreignByTable.get(table.id) || new Set(), labels },
      ariaLabel: `${table.schema}.${table.object.object_name}`,
    };
  });
  const edges: Edge[] = relations.map((relation, index) => ({
    id: `${relation.sourceId}-${relation.targetId}-${index}`,
    source: relation.sourceId, target: relation.targetId,
    label: relation.label,
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
    className: "er-relation-edge",
  }));
  return { nodes, edges };
}

function DiagramCanvas({ schemas, scope, labels }: { schemas: ErSchema[]; scope: ErScope; labels: ErLabels }) {
  const [direction, setDirection] = useState<"LR" | "TB">("LR");
  const [search, setSearch] = useState("");
  const [showColumns, setShowColumns] = useState(true);
  const exportRef = useRef<HTMLDivElement>(null);
  const { fitView } = useReactFlow();
  const catalog = useMemo(() => new Map(schemas.flatMap((schema) =>
    schema.objects.map((object) => [qualified(schema.name, object.object_name), { id: qualified(schema.name, object.object_name), schema: schema.name, object }])
  )), [schemas]);

  const graphData = useMemo(() => {
    let tables: DiagramTable[] = [];
    let queryJoins: QueryJoin[] = [];
    if (scope.kind === "schema") {
      tables = schemas.find((schema) => schema.name === scope.schema)?.objects.map((object) => ({
        id: qualified(scope.schema, object.object_name), schema: scope.schema, object,
      })) || [];
    } else if (scope.kind === "table") {
      const rootId = qualified(scope.schema, scope.table);
      const root = catalog.get(rootId);
      if (root) {
        const related = new Set([rootId]);
        for (const relation of root.object.relations) related.add(qualified(relation.target_schema, relation.target_table));
        for (const candidate of catalog.values()) {
          if (candidate.object.relations.some((relation) => qualified(relation.target_schema, relation.target_table) === rootId)) related.add(candidate.id);
        }
        tables = [...related].map((id) => catalog.get(id)).filter((item): item is DiagramTable => Boolean(item));
      }
    } else {
      const parsed = parseQuery(scope.sql);
      tables = parsed.ids.map((id) => catalog.get(id)).filter((item): item is DiagramTable => Boolean(item));
      queryJoins = parsed.joins;
    }
    const ids = new Set(tables.map((table) => table.id));
    const catalogRelations: QueryJoin[] = tables.flatMap((table) => table.object.relations
      .filter((relation) => ids.has(qualified(relation.target_schema, relation.target_table)))
      .map((relation) => ({
        sourceId: table.id,
        targetId: qualified(relation.target_schema, relation.target_table),
        sourceColumn: relation.column_name,
        targetColumn: relation.target_column,
        label: `${relation.column_name} → ${relation.target_column}`,
      })));
    const seen = new Set<string>();
    const relations = [...catalogRelations, ...queryJoins].filter((relation) => {
      const key = `${relation.sourceId}:${relation.targetId}:${relation.sourceColumn}:${relation.targetColumn}`;
      if (seen.has(key)) return false;
      seen.add(key); return true;
    });
    return layoutElements(tables, relations, direction, labels);
  }, [schemas, catalog, scope, direction, labels]);

  const [nodes, setNodes, onNodesChange] = useNodesState(graphData.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(graphData.edges);
  useEffect(() => {
    setNodes(graphData.nodes); setEdges(graphData.edges);
    window.setTimeout(() => fitView({ padding: .18, duration: 350 }), 50);
  }, [graphData, fitView, setEdges, setNodes]);
  useEffect(() => {
    const term = search.trim().toLowerCase();
    setNodes((current) => current.map((node) => ({
      ...node,
      className: term && !`${node.data.schema}.${node.data.object.object_name}`.toLowerCase().includes(term) ? "er-dimmed" : "",
    })));
  }, [search, setNodes]);
  useEffect(() => {
    const root = exportRef.current;
    root?.classList.toggle("hide-columns", !showColumns);
    window.setTimeout(() => fitView({ padding: .18 }), 30);
  }, [showColumns, fitView]);

  const exportPng = useCallback(async () => {
    if (!exportRef.current) return;
    const dataUrl = await toPng(exportRef.current, { pixelRatio: 2, backgroundColor: "#171724" });
    const link = document.createElement("a");
    link.download = `upexnote-er-${Date.now()}.png`;
    link.href = dataUrl;
    link.click();
  }, []);

  return <div className="er-diagram-shell">
    <header className="er-toolbar">
      <label><Search size={14} /><input value={search} onChange={(event) => setSearch(event.currentTarget.value)} placeholder={labels.findTable} /></label>
      <div className="er-toolbar-group">
        <button className={`secondary${showColumns ? " active" : ""}`} onClick={() => setShowColumns((value) => !value)}><Columns3 size={14} />{labels.columns}</button>
        <button className="secondary" onClick={() => setDirection((value) => value === "LR" ? "TB" : "LR")}><Maximize2 size={14} />{direction === "LR" ? labels.horizontal : labels.vertical}</button>
        <button className="secondary" onClick={() => fitView({ padding: .18, duration: 300 })}><Maximize2 size={14} />{labels.fit}</button>
        <button className="secondary" onClick={exportPng}><Download size={14} />PNG</button>
      </div>
    </header>
    <div className="er-canvas" ref={exportRef}>
      {nodes.length ? <ReactFlow
        nodes={nodes} edges={edges} nodeTypes={nodeTypes}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        nodesConnectable={false} elementsSelectable nodesFocusable edgesFocusable
        fitView minZoom={0.15} maxZoom={1.8} proOptions={{ hideAttribution: true }}
      >
        <Background gap={22} size={1} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable nodeColor="var(--accent)" maskColor="color-mix(in srgb, var(--bg) 70%, transparent)" />
      </ReactFlow> : <div className="er-empty"><Table2 size={32} /><strong>{labels.noTables}</strong><span>{labels.noTablesHelp}</span></div>}
    </div>
    <footer className="er-legend">
      <span><KeyRound size={12} />PK</span><span><b>FK</b>{labels.foreignKey}</span><span><i>NN</i>{labels.notNull}</span>
      <span>{nodes.length} {labels.tables}</span><span>{edges.length} {labels.relations}</span>
    </footer>
  </div>;
}

export default function ErDiagram(props: { schemas: ErSchema[]; scope: ErScope; labels: ErLabels }) {
  return <ReactFlowProvider><DiagramCanvas {...props} /></ReactFlowProvider>;
}
