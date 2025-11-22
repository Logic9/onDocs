import { UploadCloud } from "lucide-react";

const DragDropOverlay = () => {
  return (
    <div className="absolute inset-0 z-70 bg-white/60 backdrop-blur-md flex items-center justify-center p-6 animate-in fade-in duration-200 pointer-events-none">
      <div className="w-full h-full border-4 border-dashed border-blue-400 rounded-3xl flex flex-col items-center justify-center relative overflow-hidden bg-blue-50/30">
        <div className="absolute inset-0 bg-linear-to-br from-blue-100/0 via-blue-100/20 to-blue-100/0 pointer-events-none" />

        <div className="bg-white p-8 rounded-full shadow-2xl mb-8 text-blue-600 animate-bounce ring-8 ring-blue-100">
          <UploadCloud size={64} strokeWidth={1.5} />
        </div>

        <h2 className="text-4xl font-bold text-gray-800 mb-3 tracking-tight">
          파일을 여기에 놓으세요
        </h2>
        <p className="text-blue-500 font-medium text-lg">
          onDocs AI가 즉시 분석을 시작합니다
        </p>

        <div className="mt-8 flex gap-4">
          <span className="px-3 py-1 rounded-md bg-white border border-gray-200 text-xs font-bold text-gray-500">
            PDF
          </span>
          <span className="px-3 py-1 rounded-md bg-white border border-gray-200 text-xs font-bold text-gray-500">
            TXT
          </span>
          <span className="px-3 py-1 rounded-md bg-white border border-gray-200 text-xs font-bold text-gray-500">
            MD
          </span>
        </div>
      </div>
    </div>
  );
};

export default DragDropOverlay;
