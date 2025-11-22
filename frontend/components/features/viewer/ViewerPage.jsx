import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle } from "lucide-react";
import { normalizeText } from "@/utils/textUtils";
import {
  Highlighter,
  ParagraphRenderer,
  ListItemRenderer,
} from "./MarkdownComponents";

const ViewerPage = memo(
  ({ page, isActive, hasRisk, riskResults, onRef, onClick }) => {
    const pageRisks = useMemo(() => {
      return riskResults
        .filter((r) => r.page_number === page.page_number)
        .map((r) => ({
          clean: normalizeText(r.content),
          id: `risk-${r.page_number}-${normalizeText(r.content).slice(0, 30)}`,
        }));
    }, [riskResults, page.page_number]);

    return (
      <div
        ref={onRef}
        onClick={() => onClick(page.page_number)}
        className={`group relative bg-white rounded-xl border p-6 cursor-pointer transition-all duration-300 ease-out ${
          isActive
            ? "border-blue-500 ring-4 ring-blue-50 shadow-xl scale-[1.01] z-10"
            : "border-gray-200 hover:border-blue-200 hover:shadow-md"
        } ${hasRisk ? "bg-amber-50/30 border-amber-200" : ""}`}
      >
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-100">
          <span
            className={`text-[10px] font-bold tracking-wider uppercase px-2 py-1 rounded-md transition-colors ${
              isActive
                ? "bg-blue-100 text-blue-700"
                : "bg-gray-100 text-gray-500 group-hover:bg-white"
            }`}
          >
            Page {page.page_number}
          </span>
          {hasRisk && (
            <span className="flex items-center gap-1.5 text-[10px] font-bold text-amber-600 bg-amber-100 px-2.5 py-1 rounded-full animate-pulse">
              <AlertTriangle size={12} /> <span>주의 사항 포함</span>
            </span>
          )}
        </div>

        <div className="prose prose-sm max-w-none text-gray-800 wrap-break-word leading-normal">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => (
                <h1 className="text-lg font-bold mb-2 mt-3 border-b pb-1">
                  <Highlighter
                    pageRisks={pageRisks}
                    as="span"
                    className="p-0! bg-transparent! shadow-none! border-0! block"
                  >
                    {children}
                  </Highlighter>
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-base font-semibold mb-1.5 mt-2">
                  <Highlighter
                    pageRisks={pageRisks}
                    as="span"
                    className="p-0! bg-transparent! shadow-none! border-0! block"
                  >
                    {children}
                  </Highlighter>
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold mb-1 mt-2">
                  <Highlighter
                    pageRisks={pageRisks}
                    as="span"
                    className="p-0! bg-transparent! shadow-none! border-0! block"
                  >
                    {children}
                  </Highlighter>
                </h3>
              ),
              p: (props) => (
                <ParagraphRenderer {...props} pageRisks={pageRisks} />
              ),
              li: (props) => (
                <ListItemRenderer {...props} pageRisks={pageRisks} />
              ),
              ul: ({ children }) => (
                <ul className="list-disc pl-5 mb-2 space-y-1 text-gray-700">
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal pl-5 mb-2 space-y-1 text-gray-700">
                  {children}
                </ol>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-blue-200 pl-4 py-1 my-2 bg-blue-50/30 rounded-r italic text-gray-600">
                  <Highlighter pageRisks={pageRisks}>{children}</Highlighter>
                </blockquote>
              ),
              code: ({ children }) => (
                <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-gray-600 break-all">
                  {children}
                </code>
              ),
              pre: ({ children }) => (
                <pre className="bg-gray-900/5 p-3 rounded-lg overflow-x-auto my-2 text-xs font-mono text-gray-700 whitespace-pre-wrap break-all border border-gray-200/50 leading-normal">
                  {children}
                </pre>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto my-3 border rounded-lg">
                  <table className="min-w-full divide-y divide-gray-200 text-sm leading-normal">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-gray-50">{children}</thead>
              ),
              th: ({ children }) => (
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b wrap-break-word">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-3 py-2 whitespace-nowrap border-b last:border-0 text-gray-600 wrap-break-word">
                  {children}
                </td>
              ),
            }}
          >
            {page.content}
          </ReactMarkdown>
        </div>
      </div>
    );
  }
);

ViewerPage.displayName = "ViewerPage";
export default ViewerPage;
