export function buildGraphData(analysis, width = 800, height = 420) {
  const { targeted_node: targetedNode, affected_components: components = [] } = analysis

  const maxHop = Math.max(...components.map((c) => c.hop_distance ?? 1), 1)
  const canvasMin = Math.min(width, height)
  const ringStep = Math.max(110, canvasMin * 0.22 / maxHop)

  const centerNode = {
    id: targetedNode,
    name: targetedNode,
    risk_level: 'Target',
    isTarget: true,
    hop_distance: 0,
    x: 0,
    y: 0,
    fx: 0,
    fy: 0,
  }

  const nodes = [centerNode]
  const links = []
  const byHop = {}

  components.forEach((component) => {
    nodes.push({
      id: component.node_id,
      name: component.node_id,
      risk_level: component.risk_level,
      hop_distance: component.hop_distance,
      isTarget: false,
    })

    links.push({
      source: targetedNode,
      target: component.node_id,
    })

    const hop = component.hop_distance ?? 1
    if (!byHop[hop]) byHop[hop] = []
    byHop[hop].push(component.node_id)
  })

  Object.entries(byHop).forEach(([hop, ids]) => {
    const radius = Number(hop) * ringStep
    const angleOffset = (Math.PI / Math.max(ids.length, 1)) * 0.5

    ids.forEach((id, index) => {
      const angle = (2 * Math.PI * index) / ids.length - Math.PI / 2 + angleOffset
      const node = nodes.find((entry) => entry.id === id)
      if (node) {
        const x = radius * Math.cos(angle)
        const y = radius * Math.sin(angle)
        node.x = x
        node.y = y
        node.fx = x
        node.fy = y
      }
    })
  })

  return { nodes, links }
}
