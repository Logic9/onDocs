"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Send,
  Paperclip,
  Bot,
  User,
  Loader2,
  Cpu,
  CheckCircle2,
  FileText,
} from "lucide-react";

const API_URL = "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState([
    {
      role: "bot",
      content:
        "**onDocs AI**입니다.\n분석할 문서(PDF, TXT, MD)를 업로드 해주세요!",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [fileName, setFileName] = useState(null);

  const fileInputRef = useRef(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isLoading]);

  const checkStatus = async (filename) => {
    try {
      const res = await fetch(`${API_URL}/status/${filename}`);
      const data = await res.json();
      return data.status;
    } catch (e) {
      return "unknown";
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setStatusMessage("파일 업로드 중...");
    const formData = new FormData();
    formData.append("file", file);

    try {
      await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      setFileName(file.name);
      setStatusMessage(
        "AI가 문서를 분석하고 있습니다... (잠시만 기다려주세요)"
      );

      const pollInterval = setInterval(async () => {
        const status = await checkStatus(file.name);

        if (status === "completed") {
          clearInterval(pollInterval);
          setIsUploading(false);
          setStatusMessage("");

          setMessages([
            {
              role: "bot",
              content: `✅ **${file.name}** 분석 완료!\n이제 질문하셔도 됩니다.`,
            },
          ]);
        } else if (status === "failed") {
          clearInterval(pollInterval);
          setIsUploading(false);
          alert("문서 분석에 실패했습니다.");
          setFileName(null);
        }
      }, 1000);
    } catch (error) {
      alert("업로드 요청 실패: " + error.message);
      setIsUploading(false);
      setFileName(null);
    }
  };

  const handleSummarize = async () => {
    if (!fileName || isLoading) return;

    setIsLoading(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "📄 문서 전체를 요약해줘." },
      { role: "bot", content: "" },
    ]);

    try {
      const response = await fetch(`${API_URL}/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: fileName }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunkValue = decoder.decode(value, { stream: true });

        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMsgIndex = newMessages.length - 1;

          const lastMessage = { ...newMessages[lastMsgIndex] };
          lastMessage.content += chunkValue;

          newMessages[lastMsgIndex] = lastMessage;
          return newMessages;
        });
      }
    } catch (error) {
      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].content =
          "❌ 요약 중 오류가 발생했습니다.";
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    if (!fileName) {
      alert("먼저 문서를 업로드해주세요!");
      return;
    }

    const userMessage = input;
    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
      { role: "bot", content: "" },
    ]);
    setIsLoading(true);

    try {
      const conversationHistory = messages.slice(1).map((msg) => ({
        role: msg.role === "bot" ? "assistant" : "human",
        content: msg.content,
      }));

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage,
          history: conversationHistory, // 모든 대화 기록 전송
        }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunkValue = decoder.decode(value, { stream: true });

        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMsgIndex = newMessages.length - 1;
          const lastMessage = { ...newMessages[lastMsgIndex] };
          lastMessage.content += chunkValue;
          newMessages[lastMsgIndex] = lastMessage;
          return newMessages;
        });
      }
    } catch (error) {
      setMessages((prev) => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].content = "❌ 오류가 발생했습니다.";
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex flex-col h-screen bg-[#F3F4F6] text-slate-900 font-sans">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b px-6 py-4 flex items-center justify-between sticky top-0 z-20">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-lg text-white shadow-lg shadow-indigo-500/30">
            <Cpu size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-800 tracking-tight">
              onDocs
            </h1>
            <p className="text-xs text-slate-500 font-medium">
              100% Offline, Edge AI Document Analyzer
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {fileName && (
            <button
              onClick={handleSummarize}
              disabled={isLoading || isUploading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 hover:border-indigo-500 hover:text-indigo-600 text-slate-600 hover:shadow-md cursor-pointer active:scale-95 transition-all duration-200 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileText className="w-4 h-4" />
              <span>전체 요약</span>
            </button>
          )}
          <input
            type="file"
            accept=".pdf,.txt,.md"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current.click()}
            disabled={isUploading}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-200 text-sm font-semibold shadow-sm
              ${
                isUploading
                  ? "bg-indigo-50 text-indigo-600 border border-indigo-200 cursor-wait"
                  : "bg-white border border-slate-200 hover:border-indigo-500 hover:text-indigo-600 text-slate-600 hover:shadow-md cursor-pointer active:scale-95"
              }`}
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>분석 중...</span>
              </>
            ) : (
              <>
                {fileName ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <Paperclip className="w-4 h-4" />
                )}
                <span className="truncate max-w-[150px]">
                  {fileName ? fileName : "문서 업로드"}
                </span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* 채팅 영역 래퍼 (상대 좌표 기준점) */}
      <div className="flex-1 relative overflow-hidden">
        {/* 실제 스크롤 되는 채팅 영역 */}
        <div
          ref={chatContainerRef}
          className="h-full overflow-y-auto p-4 space-y-6 scroll-smooth"
        >
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex w-full ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`flex max-w-[85%] lg:max-w-[70%] items-start gap-3 ${
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                <div
                  className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-sm
                  ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white"
                      : "bg-white border border-slate-200 text-slate-600"
                  }`}
                >
                  {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div
                  className={`px-5 py-3.5 shadow-sm text-sm leading-relaxed min-h-11 flex items-center
                  ${
                    msg.role === "user"
                      ? "bg-indigo-600 text-white rounded-2xl rounded-tr-sm"
                      : "bg-white border border-slate-100 text-slate-800 rounded-2xl rounded-tl-sm"
                  }`}
                >
                  {/* 생각 중 애니메이션 (일반 채팅)*/}
                  {msg.role === "bot" && msg.content === "" ? (
                    <div className="flex items-center gap-1 h-6">
                      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></span>
                    </div>
                  ) : /* 요약 전용 애니메이션 */
                  msg.role === "bot" && msg.content === "__SUMMARIZING__" ? (
                    <div className="flex items-center gap-3 text-indigo-600 py-1">
                      <div className="relative">
                        <FileText className="w-5 h-5" />
                        <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-indigo-500 rounded-full animate-ping opacity-75"></span>
                      </div>
                      <span className="font-medium animate-pulse">
                        전체 문서를 요약하고 있습니다...
                      </span>
                    </div>
                  ) : /* 일반 텍스트 메시지 (봇) */
                  msg.role === "bot" ? (
                    <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0 prose-strong:text-indigo-600 prose-strong:font-bold prose-pre:bg-slate-100 prose-pre:text-slate-700 prose-pre:p-2 prose-pre:rounded-lg">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    /* 사용자 메시지 */
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 분석 중 오버레이 */}
        {isUploading && (
          <div className="absolute inset-0 bg-white/60 backdrop-blur-sm flex flex-col items-center justify-center z-50 transition-all duration-300">
            <div className="bg-white p-8 rounded-3xl shadow-2xl border border-indigo-100 text-center max-w-sm mx-4 transform scale-100 animate-in fade-in zoom-in duration-200">
              <div className="relative w-16 h-16 mx-auto mb-6">
                <div className="absolute inset-0 border-4 border-indigo-100 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
                <Cpu className="absolute inset-0 m-auto text-indigo-600 w-6 h-6 animate-pulse" />
              </div>
              <h3 className="text-xl font-bold text-slate-800 mb-2">
                AI 문서 분석 중
              </h3>
              <p className="text-sm text-slate-500 font-medium">
                {statusMessage}
              </p>
              <div className="mt-6 flex justify-center gap-1">
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></span>
              </div>
              <p className="text-xs text-slate-400 mt-4">
                페이지 수에 따라 시간이 소요될 수 있습니다.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 입력 영역 */}
      <div className="p-4 bg-white/80 backdrop-blur-sm border-t border-slate-100">
        <form
          onSubmit={handleSendMessage}
          className="max-w-4xl mx-auto relative flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              fileName ? "질문을 입력하세요." : "문서를 업로드해주세요."
            }
            disabled={!fileName || isLoading || isUploading}
            className="flex-1 bg-slate-100 border-transparent focus:bg-white border focus:border-indigo-500 rounded-full px-6 py-3.5 text-sm transition-all outline-none shadow-inner focus:shadow-lg focus:shadow-indigo-100 disabled:opacity-60 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!fileName || isLoading || !input.trim() || isUploading}
            className="disabled:cursor-not-allowed cursor-pointer bg-indigo-600 hover:bg-indigo-700 disabled:hover:bg-indigo-600 text-white p-3 rounded-full shadow-lg shadow-indigo-300 hover:shadow-indigo-400 transition-all disabled:opacity-50 disabled:shadow-none transform active:scale-95 disabled:active:scale-100"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
        <div className="text-center mt-2">
          <p className="text-[10px] text-slate-400">
            Powered by Local LLM • 100% Offline Secure
          </p>
        </div>
      </div>
    </main>
  );
}
