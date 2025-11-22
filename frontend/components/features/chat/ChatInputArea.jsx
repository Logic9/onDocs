import { Paperclip, Send, Search, AlertTriangle } from "lucide-react";

const ChatInputArea = ({
  input,
  setInput,
  handleSend,
  isLoading,
  fileName,
  isUploading,
  handleFileInputChange,
  fileInputRef,
  searchResults,
  riskResults,
  onReferenceClick,
}) => {
  return (
    <div className="shrink-0 px-6 pb-6 pt-2 bg-white border-t border-transparent z-40">
      <div className="max-w-3xl mx-auto relative flex flex-col gap-3">
        {(searchResults.length > 0 || riskResults.length > 0) && (
          <div className="bg-white border border-gray-200 shadow-xl rounded-2xl overflow-hidden max-h-48 overflow-y-auto custom-scrollbar animate-in slide-in-from-bottom-2 fade-in">
            {searchResults.length > 0 && (
              <div className="p-3 border-b border-gray-100 last:border-0">
                <div className="flex items-center gap-2 mb-2 text-[11px] font-bold text-gray-400 uppercase tracking-wider px-1">
                  <Search size={10} /> 관련 문단 탐지
                </div>
                <div className="flex flex-col gap-1.5">
                  {searchResults.map((r, idx) => (
                    <button
                      key={idx}
                      onClick={() => onReferenceClick(r.page_number, r.content)}
                      className="cursor-pointer flex items-start gap-3 text-left p-2.5 rounded-lg hover:bg-blue-50 transition-colors group border border-transparent hover:border-blue-100"
                    >
                      <span className="shrink-0 text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded group-hover:bg-white">
                        P.{r.page_number}
                      </span>
                      <span className="text-xs text-gray-600 line-clamp-1">
                        {r.content}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {riskResults.length > 0 && (
              <div className="p-3">
                <div className="flex items-center gap-2 mb-2 text-[11px] font-bold text-amber-600/70 uppercase tracking-wider px-1">
                  <AlertTriangle size={10} /> 주의 조항/제약 사항
                </div>
                <div className="flex flex-col gap-1.5">
                  {riskResults.map((r, idx) => (
                    <button
                      key={idx}
                      onClick={() => onReferenceClick(r.page_number, r.content)}
                      className="cursor-pointer flex items-start gap-3 text-left p-2.5 rounded-lg hover:bg-amber-50 transition-colors group border border-transparent hover:border-amber-100"
                    >
                      <span className="shrink-0 text-[10px] font-bold text-amber-600 bg-amber-100 px-1.5 py-0.5 rounded group-hover:bg-white">
                        P.{r.page_number}
                      </span>
                      <span className="text-xs text-gray-600 line-clamp-1">
                        {r.content}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-2 flex items-center gap-2 focus-within:ring-2 focus-within:ring-blue-100 transition-shadow">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="cursor-pointer p-2.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors relative"
            disabled={isUploading}
          >
            <Paperclip size={20} />
          </button>
          <input
            type="file"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept=".pdf,.txt"
          />
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={
              fileName
                ? "문서 내용에 대해 질문하세요."
                : "문서를 업로드하거나 드래그하세요."
            }
            disabled={!fileName || isLoading}
            className="flex-1 bg-transparent border-none focus:ring-0 text-sm placeholder:text-gray-400 py-2 outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className={`p-2.5 rounded-xl transition-all duration-200 ${
              input.trim() && !isLoading
                ? "bg-blue-600 text-white shadow-md hover:bg-blue-700 transform active:scale-95 cursor-pointer"
                : "bg-gray-100 text-gray-300 cursor-not-allowed"
            }`}
          >
            <Send size={18} />
          </button>
        </div>
        <div className="text-center">
          <span className="text-[10px] text-gray-400 font-medium tracking-wide">
            Powered by Local LLM • 100% Offline Secure Analysis
          </span>
        </div>
      </div>
    </div>
  );
};

export default ChatInputArea;
