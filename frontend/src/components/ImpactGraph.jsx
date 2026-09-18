import { useEffect, useMemo, useRef } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { buildGraphData } from '../utils/graphData'
import { getRiskColor } from '../utils/risk'

function drawNodeLabel(ctx, text, x, y, globalScale) {
  const fontSize = Math.max(12 / globalScale, 10)
  ctx.font = `600 ${fontSize}px 'JetBrains Mono', monospace`
  const metrics = ctx.measureText(text)
  const padX = 8 / globalScale
  const padY = 4 / globalScale
  const boxWidth = metrics.width + padX * 2
  const boxHeight = fontSize + padY * 2

  ctx.fillStyle = 'rgba(26, 24, 37, 0.94)'
  ctx.strokeStyle = 'rgba(245, 158, 11, 0.3)'
  ctx.lineWidth = 1 / globalScale
  ctx.beginPath()
  ctx.roundRect(x - boxWidth / 2, y, boxWidth, boxHeight, 6 / globalScale)
  ctx.fill()
  ctx.stroke()

  ctx.fillStyle = '#e5e7eb'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  ctx.fillText(text, x, y + padY)
}

export default function ImpactGraph({ analysis, width, height }) {
  const graphRef = useRef(null)
  const graphData = useMemo(
    () => buildGraphData(analysis, width, height),
    [analysis, width, height],
  )

  useEffect(() => {
    const graph = graphRef.current
    if (!graph) return undefined

    const timer = window.setTimeout(() => {
      graph.zoomToFit(500, 80)
    }, 150)

    return () => window.clearTimeout(timer)
  }, [graphData, width, height])

  return (
    <div className="graph-container">
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={width}
        height={height}
        backgroundColor="rgba(15, 14, 23, 0.5)"
        nodeRelSize={8}
        linkColor={() => 'rgba(184, 180, 194, 0.48)'}
        linkWidth={2}
        linkDirectionalParticles={3}
        linkDirectionalParticleWidth={2.5}
        linkDirectionalParticleSpeed={0.006}
        linkDirectionalParticleColor={() => 'rgba(245, 158, 11, 0.85)'}
        warmupTicks={0}
        cooldownTicks={0}
        enableNodeDrag={false}
        enableZoomInteraction
        enablePanInteraction
        nodeCanvasObjectMode={() => 'replace'}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const radius = node.isTarget ? 18 : 12
          const color = node.isTarget ? '#f59e0b' : getRiskColor(node.risk_level)

          ctx.beginPath()
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false)
          ctx.fillStyle = color
          ctx.fill()

          ctx.strokeStyle = node.isTarget ? '#e5e7eb' : 'rgba(229, 231, 235, 0.35)'
          ctx.lineWidth = (node.isTarget ? 3 : 1.5) / globalScale
          ctx.stroke()

          if (node.isTarget) {
            ctx.beginPath()
            ctx.arc(node.x, node.y, radius + 6 / globalScale, 0, 2 * Math.PI, false)
            ctx.strokeStyle = 'rgba(245, 158, 11, 0.38)'
            ctx.lineWidth = 2 / globalScale
            ctx.stroke()
          }

          const label = node.name ?? node.id
          drawNodeLabel(ctx, label, node.x, node.y + radius + 10 / globalScale, globalScale)
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          const radius = node.isTarget ? 22 : 16
          ctx.beginPath()
          ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false)
          ctx.fillStyle = color
          ctx.fill()
        }}
      />
    </div>
  )
}
