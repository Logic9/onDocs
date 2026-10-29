"use client";

import { useState, useRef, useEffect } from "react";
import { normalizeText } from "@/utils/textUtils";

import Header from "@/components/layout/Header";
import DragDropOverlay from "@/components/common/DragDropOverlay";
import AnalysisModal from "@/components/common/AnalysisModal";
import ThinkingIndicator from "@/components/common/ThinkingIndicator";
import MessageItem from "@/components/features/chat/MessageItem";
import ChatInputArea from "@/components/features/chat/ChatInputArea";
import DocumentViewer from "@/components/features/viewer/DocumentViewer";

import { useFileHandler } from "@/hooks/useFileHandler";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const {
    isUploading,
    isAnalyzing,
    statusMessage,
    progress,
    etaSec,
    elapsedSec,
    fileName,
    pages,
    riskResults,
    uploadFile,
    setSearchResults: setFileSearchResults,
  } = useFileHandler();

  const {
    messages,
    setMessages,
    input,
    setInput,
    isLoading,
    thinkingStep,
    searchResults,
    setSearchResults,
    sendMessage,
    addMessage,
    modelPreference,
    setModelPreference,
    selectedModel,
  } = useChat();

  const [showViewer, setShowViewer] = useState(false);
  const [activePage, setActivePage] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);
  const chatContainerRef = useRef(null);
  const pageRefs = useRef({});

  useEffect(() => {
    if (chatContainerRef.current)
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
  }, [messages, isLoading, thinkingStep]);

  const handleUpload = (file) => {
    setSearchResults([]);
    setActivePage(null);
    setShowViewer(false);

    uploadFile(file, {
      onStatusUpdate: (msg) => addMessage("bot", msg),

      onComplete: (loadedPages) => {
        if (loadedPages.length > 0) {
          setActivePage(loadedPages[0].page_number);
          setShowViewer(true);
        }
        setMessages([
          {
            role: "bot",
            content:
              "**분석이 완료되었습니다!**\n\n이제 문서에 대해 질문하거나 요약을 요청해보세요. 우측 뷰어에서 **특이사항 리포트**도 확인하실 수 있습니다.",
          },
        ]);
      },
      onFail: (msg) => addMessage("bot", msg),
    });
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files?.[0];
    handleUpload(file);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget)) return;
    setIsDragging(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (
        file.name.endsWith(".pdf") ||
        file.name.endsWith(".txt") ||
        file.name.endsWith(".md")
      ) {
        handleUpload(file);
      } else {
        alert("지원하지 않는 파일 형식입니다. (PDF, TXT 지원)");
      }
    }
  };

  const handleSend = () => {
    sendMessage(fileName, (results) => {
      if (results?.length > 0) {
        const firstPage = results[0].page_number;
        if (firstPage != null) {
          setShowViewer(true);
          setActivePage(firstPage);
          setTimeout(() => {
            const ref = pageRefs.current[firstPage];
            if (ref) ref.scrollIntoView({ behavior: "smooth", block: "start" });
          }, 100);
        }
      }
    });
  };

  const handleClickReference = (pageNumber, content) => {
    if (pageNumber == null) return;
    setShowViewer(true);
    setActivePage(pageNumber);
    setTimeout(() => {
      const targetId = `risk-${pageNumber}-${normalizeText(content).slice(
        0,
        30
      )}`;
      const targetElement = document.getElementById(targetId);
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: "smooth", block: "center" });
        targetElement.classList.add(
          "ring-4",
          "ring-blue-200",
          "transition-all",
          "duration-500"
        );
        setTimeout(
          () => targetElement.classList.remove("ring-4", "ring-blue-200"),
          2000
        );
      } else {
        const ref = pageRefs.current[pageNumber];
        if (ref) ref.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 300);
  };

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className="flex h-screen bg-white overflow-hidden font-sans text-gray-900 relative"
    >
      {isAnalyzing && (
        <AnalysisModal
          status={statusMessage}
          fileName={fileName}
          progress={progress}
          etaSec={etaSec}
          elapsedSec={elapsedSec}
        />
      )}

      {isDragging && <DragDropOverlay />}

      <Header
        fileName={fileName}
        statusMessage={statusMessage}
        showViewer={showViewer}
        setShowViewer={setShowViewer}
      />

      <div className="flex-1 flex w-full pt-16 overflow-hidden">
        <div
          className={`flex flex-col h-full transition-all duration-500 ease-in-out min-w-0 bg-white ${
            showViewer ? "w-full md:w-1/2 lg:w-[55%]" : "w-full"
          }`}
        >
          <div
            className="flex-1 overflow-y-auto relative scroll-smooth"
            ref={chatContainerRef}
          >
            <div className="max-w-3xl mx-auto px-6 py-8 min-h-full flex flex-col justify-end">
              {messages.length === 0 && <div className="flex-1" />}
              {messages.map((m, i) => (
                <MessageItem key={i} msg={m} />
              ))}
              <ThinkingIndicator step={thinkingStep} />
            </div>
          </div>

          <ChatInputArea
            input={input}
            setInput={setInput}
            handleSend={handleSend}
            isLoading={isLoading}
            fileName={fileName}
            isUploading={isUploading}
            handleFileInputChange={handleFileInputChange}
            fileInputRef={fileInputRef}
            searchResults={searchResults}
            riskResults={riskResults}
            onReferenceClick={handleClickReference}
            modelPreference={modelPreference}
            setModelPreference={setModelPreference}
            selectedModel={selectedModel}
          />
        </div>

        <DocumentViewer
          show={showViewer}
          pages={pages}
          activePage={activePage}
          riskResults={riskResults}
          onClose={() => setShowViewer(false)}
          onPageClick={setActivePage}
          pageRefs={pageRefs}
        />

        {showViewer && (
          <div
            className="md:hidden fixed inset-0 bg-black/20 backdrop-blur-sm z-20 animate-in fade-in duration-300"
            onClick={() => setShowViewer(false)}
          />
        )}
      </div>
    </div>
  );
}
