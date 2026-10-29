import {
  Cpu,
  FileText,
  Paperclip,
  PanelRightClose,
  PanelRightOpen,
} from "lucide-react";

const Header = ({ fileName, statusMessage, showViewer, setShowViewer }) => {
  return (
    <header className="h-16 px-4 md:px-6 border-b border-gray-200 bg-white flex items-center justify-between shrink-0 z-40 w-full fixed top-0 left-0 right-0">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="bg-blue-600 p-1.5 rounded-lg shadow-sm">
          <Cpu className="text-white" size={18} />
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-tight text-gray-900">
            onDocs AI
          </h1>
          <p className="text-[10px] text-gray-500 font-medium">
            Universal Document Analysis
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3 min-w-0">
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all max-w-[220px] sm:max-w-[320px] min-w-0 ${
            fileName
              ? "bg-blue-50 text-blue-700 border border-blue-100"
              : "bg-gray-50 text-gray-500 border border-gray-200"
          }`}
        >
          {fileName ? <FileText size={14} /> : <Paperclip size={14} />}
          <span className="truncate min-w-0">{fileName || "문서 없음"}</span>
          {statusMessage && (
            <>
              <div className="w-px h-3 bg-current opacity-20 mx-1" />
              <span className="opacity-80 truncate min-w-0 whitespace-nowrap">
                {statusMessage}
              </span>
            </>
          )}
        </div>
        {fileName && (
          <button
            onClick={() => setShowViewer(!showViewer)}
            className={`p-2 rounded-full transition-colors ${
              showViewer
                ? "bg-blue-50 text-blue-600"
                : "hover:bg-gray-100 text-gray-500"
            }`}
            title="문서 뷰어 토글"
          >
            {showViewer ? (
              <PanelRightClose size={18} className="cursor-pointer" />
            ) : (
              <PanelRightOpen size={18} className="cursor-pointer" />
            )}
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;
