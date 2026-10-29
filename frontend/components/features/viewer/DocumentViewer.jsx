import { FileText, X } from "lucide-react";
import ViewerPage from "./ViewerPage";
import RiskDashboard from "../analysis/RiskDashboard";

const DocumentViewer = ({
  show,
  pages,
  activePage,
  riskResults,
  onClose,
  onPageClick,
  pageRefs,
}) => {
  const pageHasRisk = (pageNumber) =>
    riskResults.some((r) => r.page_number === pageNumber);

  return (
    <div
      className={`bg-white md:border-l border-gray-200 overflow-hidden flex flex-col transition-all duration-500 ease-in-out z-40
      fixed inset-0 top-16 md:static md:inset-auto
      ${show ? "translate-x-0 opacity-100" : "translate-x-full opacity-0 pointer-events-none"}
      md:w-1/2 lg:w-[45%]`}
    >
      <div className="h-14 px-4 md:px-5 border-b border-gray-100 flex items-center justify-between bg-white shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="bg-blue-50 p-1.5 rounded-md text-blue-600">
            <FileText size={18} />
          </div>
          <span className="font-bold text-sm text-gray-800">문서 뷰어</span>
        </div>
        <button
          onClick={onClose}
          className="cursor-pointer p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X size={20} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto bg-gray-50/50 p-4 md:p-6 space-y-6 scroll-smooth">
        {pages.length > 0 && <RiskDashboard riskResults={riskResults} />}
        {pages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
            <div className="bg-gray-100 p-4 rounded-full">
              <FileText size={32} className="opacity-20" />
            </div>
            <p className="text-sm font-medium">
              문서 내용이 여기에 표시됩니다.
            </p>
          </div>
        ) : (
          pages.map((p) => (
            <ViewerPage
              key={p.page_number}
              page={p}
              isActive={p.page_number === activePage}
              hasRisk={pageHasRisk(p.page_number)}
              riskResults={riskResults}
              onRef={(el) => {
                if (pageRefs.current) {
                  pageRefs.current[p.page_number] = el;
                }
              }}
              onClick={onPageClick}
            />
          ))
        )}
      </div>
    </div>
  );
};

export default DocumentViewer;
