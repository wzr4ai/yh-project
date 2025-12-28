export function normalizePositiveInt(value, fallback = 1) {
  const num = parseInt(value, 10)
  if (!Number.isFinite(num) || num <= 0) return fallback
  return num
}

export function piecesPerBox(item) {
  const units = normalizePositiveInt(item?.units_per_box, 1)
  const pieces = normalizePositiveInt(item?.pieces_per_unit, 1)
  return units * pieces
}

export function splitStock(totalPieces, item) {
  const total = Math.max(0, Math.floor(Number(totalPieces) || 0))
  const perBox = piecesPerBox(item)
  const perUnit = normalizePositiveInt(item?.pieces_per_unit, 1)
  const boxes = Math.floor(total / perBox)
  const remain = total % perBox
  const units = Math.floor(remain / perUnit)
  const pieces = remain % perUnit
  return { boxes, units, pieces }
}

export function formatStock(totalPieces, item) {
  const { boxes, units, pieces } = splitStock(totalPieces, item)
  if (boxes === 0 && units === 0) return `${pieces}个`
  if (boxes === 0) return `${units}包 ${pieces}个`
  return `${boxes}箱 ${units}包 ${pieces}个`
}
