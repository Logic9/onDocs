export const normalizeText = (text) => {
  if (!text) return "";
  return String(text)
    .toLowerCase()
    .replace(/[^a-z0-9가-힣]/g, "");
};

export const extractText = (nodes) => {
  if (!nodes) return "";
  if (typeof nodes === "string") return nodes;
  if (typeof nodes === "number") return String(nodes);
  if (Array.isArray(nodes)) return nodes.map(extractText).join("");
  if (nodes.props && nodes.props.children)
    return extractText(nodes.props.children);
  return "";
};
