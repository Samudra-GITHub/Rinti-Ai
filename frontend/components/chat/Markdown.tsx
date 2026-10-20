"use client";

import { Children, isValidElement, memo, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";

/** Plain text of a rendered (possibly syntax-highlighted) subtree, for copying. */
function nodeText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeText).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return nodeText(node.props.children);
  return "";
}

function CodeBlock({ children }: { children?: ReactNode }) {
  const { copy, status } = useCopyToClipboard();
  const codeElement = Children.toArray(children).find(isValidElement) as
    | React.ReactElement<{ className?: string; children?: ReactNode }>
    | undefined;
  const language = /language-([\w+#-]+)/.exec(codeElement?.props.className ?? "")?.[1];
  const text = nodeText(codeElement?.props.children).replace(/\n$/, "");

  return (
    <div className="code-block">
      <div className="code-block-bar">
        <span>{language ?? "text"}</span>
        <button
          type="button"
          onClick={() => copy(text)}
          aria-label={status === "copied" ? "Copied" : "Copy code"}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[0.72rem] text-white/55 transition-colors hover:bg-white/10 hover:text-white focus-ring"
        >
          {status === "copied" ? <Check size={13} /> : <Copy size={13} />}
          <span aria-live="polite">{status === "copied" ? "Copied" : status === "failed" ? "Copy failed" : "Copy"}</span>
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  );
}

const components: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  table: ({ children }) => (
    <div className="table-wrap">
      <table>{children}</table>
    </div>
  ),
};

interface MarkdownProps {
  content: string;
}

function MarkdownImpl({ content }: MarkdownProps) {
  return (
    <div className="prose-rinti">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: false, ignoreMissing: true }]]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// Re-parse only when the text changes: during streaming, earlier messages stay put.
export default memo(MarkdownImpl);
