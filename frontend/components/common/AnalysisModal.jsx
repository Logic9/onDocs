import { Loader2, FileText } from "lucide-react";

const AnalysisModal = ({ status, fileName }) => {
  return (
    <div className="fixed inset-0 z-60 bg-black/20 backdrop-blur-md flex items-center justify-center animate-in fade-in duration-300">
      <div className="bg-white/90 border border-white/50 shadow-2xl p-8 rounded-3xl max-w-sm w-full mx-4 relative overflow-hidden flex flex-col items-center text-center">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-32 bg-blue-400/20 rounded-full blur-3xl" />
        <div className="relative w-24 h-32 bg-white border border-gray-200 rounded-xl shadow-inner mb-6 overflow-hidden flex flex-col items-center justify-center">
          <FileText className="text-gray-300" size={40} />
          <div className="absolute inset-0 p-3 space-y-2 opacity-30">
            <div className="h-1.5 bg-gray-400 rounded w-3/4" />
            <div className="h-1.5 bg-gray-400 rounded w-full" />
            <div className="h-1.5 bg-gray-400 rounded w-5/6" />
            <div className="h-1.5 bg-gray-400 rounded w-full" />
          </div>
          <div className="absolute left-0 right-0 h-1 bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.6)] z-10 animate-scan" />
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-2">문서 분석 중</h3>
        <p className="text-sm text-gray-500 mb-6 leading-relaxed">
          <span className="font-medium text-gray-700 block mb-1">
            {fileName}
          </span>
          AI가 핵심 내용을
          <br />
          파악하고 있습니다.
        </p>

        <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-full border border-blue-100">
          <Loader2 size={14} className="animate-spin text-blue-600" />
          <span className="text-xs font-bold text-blue-700">{status}</span>
        </div>
      </div>
    </div>
  );
};

export default AnalysisModal;
