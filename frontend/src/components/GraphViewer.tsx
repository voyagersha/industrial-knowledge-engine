import React, { useEffect, useRef } from 'react';
import { Box, Paper, Typography } from '@mui/material';
import * as d3 from 'd3';

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  type: string;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  type: string;
}

interface GraphViewerProps {
  graph: {
    nodes: GraphNode[];
    edges: GraphLink[];
  };
}

const GraphViewer: React.FC<GraphViewerProps> = ({ graph }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!graph || !svgRef.current) return;

    // Clear existing content
    d3.select(svgRef.current).selectAll("*").remove();

    const width = 800;
    const height = 600;

    const svg = d3.select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("width", "100%")
      .attr("height", "100%");

    // Create arrow marker for directed edges
    svg.append("defs").append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "-0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .append("path")
      .attr("d", "M 0,-5 L 10,0 L 0,5")
      .attr("fill", "#999");

    // Create the simulation
    const simulation = d3.forceSimulation<GraphNode>(graph.nodes)
      .force("link", d3.forceLink<GraphNode, GraphLink>(graph.edges)
        .id(d => d.id)
        .distance(150))
      .force("charge", d3.forceManyBody().strength(-500))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(50));

    // Create container for the graph
    const g = svg.append("g");

    // Add zoom behavior
    svg.call(d3.zoom<SVGSVGElement, unknown>()
      .extent([[0, 0], [width, height]])
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      }));

    // Draw edges
    const links = g.append("g")
      .selectAll("line")
      .data(graph.edges)
      .enter()
      .append("g");

    links.append("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#arrowhead)");

    // Add edge labels
    links.append("text")
      .attr("font-size", "10px")
      .attr("fill", "#999")
      .attr("text-anchor", "middle")
      .text(d => d.type);

    // Create node groups
    const nodes = g.append("g")
      .selectAll("g")
      .data(graph.nodes)
      .enter()
      .append("g")
      .call(d3.drag<SVGGElement, GraphNode>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Add circles for nodes
    nodes.append("circle")
      .attr("r", 25)
      .attr("fill", d => getNodeColor(d.type));

    // Add node labels
    nodes.append("text")
      .attr("dy", ".35em")
      .attr("text-anchor", "middle")
      .attr("fill", "#fff")
      .style("font-size", "12px")
      .style("pointer-events", "none")
      .text(d => d.label);

    // Add node type labels
    nodes.append("text")
      .attr("dy", "1.5em")
      .attr("text-anchor", "middle")
      .attr("fill", "#999")
      .style("font-size", "10px")
      .style("pointer-events", "none")
      .text(d => d.type);

    function getNodeColor(type: string): string {
      const colors: { [key: string]: string } = {
        'Asset': '#4CAF50',
        'Facility': '#2196F3',
        'Department': '#9C27B0',
        'Workstation': '#FF9800',
        'Personnel': '#F44336'
      };
      return colors[type] || '#607D8B';
    }

    function dragstarted(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    // Update positions on simulation tick
    simulation.on("tick", () => {
      links.select("line")
        .attr("x1", d => (d.source as GraphNode).x!)
        .attr("y1", d => (d.source as GraphNode).y!)
        .attr("x2", d => (d.target as GraphNode).x!)
        .attr("y2", d => (d.target as GraphNode).y!);

      links.select("text")
        .attr("x", d => ((d.source as GraphNode).x! + (d.target as GraphNode).x!) / 2)
        .attr("y", d => ((d.source as GraphNode).y! + (d.target as GraphNode).y!) / 2);

      nodes.attr("transform", d => `translate(${d.x},${d.y})`);
    });

  }, [graph]);

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Knowledge Graph Preview
        </Typography>
        <Box sx={{ width: '100%', height: '600px', position: 'relative' }}>
          <svg ref={svgRef} style={{ width: '100%', height: '100%' }}></svg>
        </Box>
      </Paper>
    </Box>
  );
};

export default GraphViewer;