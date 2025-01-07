export interface Entity {
  text: string;
  label: string;
  start: number;
  end: number;
}

export interface Relationship {
  source: string;
  target: string;
  type: string;
}

export interface Ontology {
  entities: [string, string][];
  relationships: Relationship[];
  attributes: string[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
