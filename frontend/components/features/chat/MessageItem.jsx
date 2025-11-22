import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Sparkles } from "lucide-react";

const MessageItem = memo(({ msg }) => {
  const isUser = msg.role === "user";
  return (
    <div
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"} mb-4`}
    >
      <div
        className={`flex max-w-[90%] md:max-w-[80%] gap-3 ${
          isUser ? "flex-row-reverse" : "flex-row"
        }`}
      >
        <div
          className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-sm border border-gray-100 ${
            isUser ? "bg-gray-900 text-white" : "bg-white text-blue-600"
          }`}
        >
          {isUser ? <User size={16} /> : <Sparkles size={16} />}
        </div>
        <div
          className={`group relative px-4 py-3 text-sm leading-normal shadow-sm rounded-2xl ${
            isUser
              ? "bg-gray-900 text-white rounded-tr-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm"
          }`}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => (
                <p className="mb-1 last:mb-0 whitespace-pre-wrap wrap-break-word leading-normal">
                  {children}
                </p>
              ),
              a: ({ href, children }) => (
                <a
                  href={href}
                  className="text-blue-500 hover:underline break-all"
                  target="_blank"
                >
                  {children}
                </a>
              ),
              code: ({ children }) => (
                <code className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono break-all">
                  {children}
                </code>
              ),
              ul: ({ children }) => (
                <ul className="list-disc ml-4 mb-2 space-y-1">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal ml-4 mb-2 space-y-1">{children}</ol>
              ),
              li: ({ children }) => (
                <li className="leading-normal">{children}</li>
              ),
            }}
          >
            {msg.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
});

MessageItem.displayName = "MessageItem";
export default MessageItem;
