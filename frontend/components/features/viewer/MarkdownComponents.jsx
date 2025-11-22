import { Children, isValidElement } from "react";
import { AlertTriangle } from "lucide-react";
import { normalizeText, extractText } from "@/utils/textUtils";

export const Highlighter = ({
  children,
  pageRisks,
  as: Component = "div",
  className = "",
}) => {
  const textContent = extractText(children);
  const cleanContent = normalizeText(textContent);

  let matchedRiskId = null;
  let isRisk = false;

  if (cleanContent.length > 5 && pageRisks.length > 0) {
    const match = pageRisks.find(
      (risk) =>
        cleanContent.includes(risk.clean) ||
        (risk.clean.includes(cleanContent) && cleanContent.length > 10)
    );
    if (match) {
      isRisk = true;
      matchedRiskId = match.id;
    }
  }

  if (isRisk) {
    return (
      <Component
        id={matchedRiskId}
        className={`relative bg-amber-50 border border-amber-200 p-3 rounded-md my-2 shadow-sm scroll-mt-24 wrap-break-word whitespace-pre-wrap ${className}`}
      >
        {children}
        <span className="absolute -top-2.5 right-2 bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md flex items-center gap-1 select-none z-10">
          <AlertTriangle size={10} /> 주의
        </span>
      </Component>
    );
  }

  return (
    <Component
      className={`mb-2 leading-normal text-gray-700 wrap-break-word whitespace-pre-wrap ${className}`}
    >
      {children}
    </Component>
  );
};

export const ParagraphRenderer = ({ children, pageRisks }) => (
  <Highlighter pageRisks={pageRisks} as="p">
    {children}
  </Highlighter>
);

export const ListItemRenderer = ({ children, pageRisks }) => {
  const childrenArray = Children.toArray(children);
  const hasParagraph = childrenArray.some(
    (child) =>
      isValidElement(child) &&
      child.props &&
      child.props.node &&
      child.props.node.tagName === "p"
  );

  if (hasParagraph) {
    return <li className="list-item ml-4 leading-normal">{children}</li>;
  }
  return (
    <li className="list-item ml-4 leading-normal">
      <Highlighter pageRisks={pageRisks} as="span" className="block">
        {children}
      </Highlighter>
    </li>
  );
};
