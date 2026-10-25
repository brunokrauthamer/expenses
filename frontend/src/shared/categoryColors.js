const categoryPalette = [
  '#6556c8',
  '#db7894',
  '#7387d6',
  '#ddaa72',
  '#8f78cb',
  '#64a2ba',
  '#c87859',
  '#627eba',
  '#bb80b3',
  '#a18c67',
  '#c2768b',
  '#d47b71',
  '#8090b9',
];

export function categoryColor(categoryId) {
  const categoryIndex = Number(categoryId) - 1;
  return categoryPalette[
    ((categoryIndex % categoryPalette.length) + categoryPalette.length) % categoryPalette.length
  ];
}
