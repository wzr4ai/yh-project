export function calculateStandardPrice(product, categoryLookup, globalMultiplier) {
  const safeCost = Number(product.baseCostPrice) || 0;
  if (product.fixedRetailPrice !== null && product.fixedRetailPrice !== undefined) {
    return {
      price: product.fixedRetailPrice,
      basis: '例外价'
    };
  }

  const category = categoryLookup[product.categoryId];
  if (category && category.retailMultiplier) {
    return {
      price: roundPrice(safeCost * category.retailMultiplier),
      basis: '分类系数'
    };
  }

  return {
    price: roundPrice(safeCost * globalMultiplier),
    basis: '全局系数'
  };
}

function roundPrice(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}
