export const warehouseGrid = {
  width: 5,
  depth: 10,
  height: 5
}

export const unloadBays = [
  { cells: ['0-0', '1-0'], protrudeSteps: 1 },
  { cells: ['3-0', '4-0'], protrudeSteps: 1 }
]

export const unloadAreaCells = new Set(unloadBays.flatMap((bay) => bay.cells))

export const getMaxBoxId = () => {
  const accessibleDepth = Math.max(warehouseGrid.depth - 1, 0)
  const totalCells = warehouseGrid.width * accessibleDepth
  return totalCells * warehouseGrid.height
}
