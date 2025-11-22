import { Loader2, Search, FileText, Cpu } from "lucide-react";

const ThinkingIndicator = ({ step }) => {
  if (!step) return null;

  let text = "";
  let icon = <Loader2 size={14} className="animate-spin" />;

  switch (step) {
    case "analyzing":
      text = "질문 분석 중...";
      icon = <Search size={14} className="animate-pulse" />;
      break;
    case "searching":
      text = "문서 스캔 중...";
      icon = <FileText size={14} className="animate-pulse" />;
      break;
    case "generating":
      text = "답변 생성 중...";
      icon = <Cpu size={14} className="animate-pulse" />;
      break;
    default:
      break;
  }

  return (
    <div className="flex items-center gap-3 text-xs text-blue-600 font-medium ml-12 mb-4 bg-blue-50 w-fit px-4 py-2 rounded-full border border-blue-100 animate-in fade-in slide-in-from-bottom-1">
      {icon} <span>{text}</span>
    </div>
  );
};

export default ThinkingIndicator;
