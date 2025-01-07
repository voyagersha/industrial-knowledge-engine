import React, { useEffect, useRef } from 'react';
import { Box, Paper, Button } from '@mui/material';
import * as d3 from 'd3';
import { exportToNeo4j } from '../services/api';

interface GraphViewerProps {
  graph: any;
}

const GraphViewer: React.FC<GraphViewerProps> = ({ graph }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  const handleExport = async () => {
    try {
      await exportToNeo4j(graph);
      alert('Graph exported to Neo4j successfully!');
    } catch (error) {
      console.error('Error exporting to Neo4j:', error);
      alert('Error exporting graph');
    }
  };

  useEffect(() => {
    if (!graph || !svgRef.current) return;

    const width = 800;
    const height = 600;

    // Clear existing content
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    const simulation = d3.forceSimulation(graph.nodes)
      .force("link", d3.forceLink(graph.edges)
        .id((d: any) => d.id)
        .distance(100))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const links = svg.append("g")
      .selectAll("line")
      .data(graph.edges)
      .enter()
      .append("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2);

    const nodes = svg.append("g")
      .selectAll("circle")
      .data(graph.nodes)
      .enter()
      .append("circle")
      .attr("r", 5)
      .attr("fill", "#69b3a2");

    const labels = svg.append("g")
      .selectAll("text")
      .data(graph.nodes)
      .enter()
      .append("text")
      .text((d: any) => d.label)
      .attr("font-size", "12px")
      .attr("dx", 12)
      .attr("dy", 4);

    simulation.on("tick", () => {
      links
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      nodes
        .attr("cx", (d: any) => d.x)
        .attr("cy", (d: any) => d.y);

      labels
        .attr("x", (d: any) => d.x)
        .attr("y", (d: any) => d.y);
    });

  }, [graph]);

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <svg ref={svgRef}></svg>
      </Paper>
      <Button
        variant="contained"
        color="primary"
        onClick={handleExport}
      >
        Export to Neo4j
      </Button>
    </Box>
  );
};

export default GraphViewer;
