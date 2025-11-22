import { useState, useRef } from "react";
import { API_URL } from "@/utils/api";

export function useFileHandler() {
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [fileName, setFileName] = useState(null);
  const [pages, setPages] = useState([]);
  const [riskResults, setRiskResults] = useState([]);
  const isAnalyzedRef = useRef(false);

  const checkStatus = async (filename) => {
    try {
      const res = await fetch(
        `${API_URL}/status/${encodeURIComponent(filename)}`
      );
      const data = await res.json();
      return data.status;
    } catch (e) {
      return "unknown";
    }
  };

  const loadDocumentPages = async () => {
    try {
      const res = await fetch(`${API_URL}/document/pages`);
      if (!res.ok) return [];
      const data = await res.json();
      setPages(data.pages || []);
      return data.pages || [];
    } catch (e) {
      console.error(e);
      return [];
    }
  };

  const loadRiskClauses = async () => {
    try {
      const res = await fetch(`${API_URL}/risks`);
      if (!res.ok) return;
      const data = await res.json();
      setRiskResults(data.results || []);
    } catch (e) {
      console.error(e);
    }
  };

  const uploadFile = async (file, { onStatusUpdate, onComplete, onFail }) => {
    if (!file) return;
    setIsUploading(true);
    setIsAnalyzing(true);
    setStatusMessage("업로드 중...");
    setFileName(file.name);
    isAnalyzedRef.current = false;
    setPages([]);
    setRiskResults([]);

    if (onStatusUpdate)
      onStatusUpdate(`**${file.name}** 문서를 분석하고 있습니다...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        setStatusMessage("업로드 실패");
        setIsUploading(false);
        setIsAnalyzing(false);
        if (onFail) onFail("업로드 요청에 실패했습니다.");
        return;
      }
      setStatusMessage("대기열 등록됨");
      setIsUploading(false);

      setStatusMessage("AI 스캔 진행 중...");
      const interval = setInterval(async () => {
        const status = await checkStatus(file.name);
        if (status === "completed") {
          clearInterval(interval);
          setStatusMessage("준비 완료");
          setIsAnalyzing(false);
          const loadedPages = await loadDocumentPages();
          await loadRiskClauses();

          if (!isAnalyzedRef.current) {
            if (onComplete) onComplete(loadedPages);
            isAnalyzedRef.current = true;
          }
        } else if (status === "failed") {
          clearInterval(interval);
          setStatusMessage("분석 실패");
          setIsAnalyzing(false);
          if (!isAnalyzedRef.current) {
            if (onFail) onFail("죄송합니다. 문서 분석 중 오류가 발생했습니다.");
            isAnalyzedRef.current = true;
          }
        }
      }, 1000);
    } catch (error) {
      setStatusMessage("오류 발생");
      setIsUploading(false);
      setIsAnalyzing(false);
      if (onFail) onFail("네트워크 오류가 발생했습니다.");
    }
  };

  return {
    isUploading,
    isAnalyzing,
    statusMessage,
    fileName,
    pages,
    riskResults,
    uploadFile,
    setRiskResults,
    setSearchResults: () => {},
    setPages,
  };
}
