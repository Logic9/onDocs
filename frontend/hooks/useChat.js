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

  const addMessage = (role, content) => {
    setMessages((prev) => [...prev, { role, content }]);
  };

  const sendMessage = async (fileName, onSearchComplete) => {
    if (!input.trim()) return;
    const userMessage = input.trim();
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
        body: JSON.stringify({ question: userMessage, history: messages }),
      });

      if (!res.body) {
        setIsLoading(false);
        setThinkingStep(null);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let botContent = "";
      let firstChunkReceived = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (!firstChunkReceived) {
          setThinkingStep(null);
          firstChunkReceived = true;
        }
        const chunk = decoder.decode(value, { stream: true });
        botContent += chunk;

        setMessages((prev) => {
          const newMsgs = [...prev];
          const lastMsg = newMsgs[newMsgs.length - 1];
          if (lastMsg.role === "bot") {
            newMsgs[newMsgs.length - 1] = { ...lastMsg, content: botContent };
            return newMsgs;
          } else {
            return [...newMsgs, { role: "bot", content: botContent }];
          }
        });
      }
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
  };
}
