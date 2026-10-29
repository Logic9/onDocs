import { useState } from "react";
import { API_URL } from "@/utils/api";

export function useChat() {
  const [messages, setMessages] = useState([
    {
      role: "bot",
      content:
        "안녕하세요! **onDocs AI**입니다.\n계약서, 약관, 매뉴얼 등 분석하고 싶은 문서를 업로드해주세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingStep, setThinkingStep] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [modelPreference, setModelPreference] = useState("auto");
  const [selectedModel, setSelectedModel] = useState(null);

  const addMessage = (role, content) => {
    setMessages((prev) => [...prev, { role, content }]);
  };

  const sendMessage = async (fileName, onSearchComplete) => {
    if (!input.trim()) return;
    const userMessage = input.trim();
    const startTime = performance.now();
    addMessage("user", userMessage);
    setInput("");
    setIsLoading(true);

    setThinkingStep("analyzing");
    await new Promise((r) => setTimeout(r, 500));

    if (fileName) {
      setThinkingStep("searching");
      try {
        const searchRes = await fetch(`${API_URL}/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: userMessage, top_k: 5 }),
        });
        if (searchRes.ok) {
          const data = await searchRes.json();
          setSearchResults(data.results || []);
          if (data.results?.length > 0 && onSearchComplete) {
            onSearchComplete(data.results);
          }
        }
      } catch (e) {
        console.error("Search Error:", e);
      }
    }

    setThinkingStep("generating");
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage,
          history: messages,
          model_preference: modelPreference,
        }),
      });

      if (!res.body) {
        setIsLoading(false);
        setThinkingStep(null);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let botContent = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        let chunk = decoder.decode(value, { stream: true });

        // 모델 정보 태그 처리
        if (chunk.includes("__MODEL__:")) {
          const parts = chunk.split("\n");
          parts.forEach((p) => {
            if (p.startsWith("__MODEL__:")) {
              setSelectedModel(p.replace("__MODEL__:", "").trim());
            }
          });
          chunk = parts.filter((p) => !p.startsWith("__MODEL__:")).join("\n");
        }

        botContent += chunk;

        setMessages((prev) => {
          const newMsgs = [...prev];
          const lastMsg = newMsgs[newMsgs.length - 1];
          if (lastMsg.role === "bot") {
            newMsgs[newMsgs.length - 1] = {
              ...lastMsg,
              content: botContent,
              elapsedMs: lastMsg.elapsedMs ?? null,
            };
            return newMsgs;
          } else {
            return [
              ...newMsgs,
              { role: "bot", content: botContent, elapsedMs: null },
            ];
          }
        });
      }

      const elapsedMs = performance.now() - startTime;
      setMessages((prev) => {
        if (!prev.length) return prev;
        const newMsgs = [...prev];
        const lastMsg = newMsgs[newMsgs.length - 1];
        if (lastMsg.role === "bot") {
          newMsgs[newMsgs.length - 1] = { ...lastMsg, elapsedMs };
        }
        return newMsgs;
      });
    } catch (error) {
      addMessage("bot", "오류가 발생했습니다.");
    } finally {
      setIsLoading(false);
      setThinkingStep(null);
    }
  };

  return {
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
  };
}
