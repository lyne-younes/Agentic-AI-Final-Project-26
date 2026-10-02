import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./Markdown.css";

/** Renders assistant replies. Raw HTML inside the text is not rendered (react-markdown's default). */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children: linkText }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {linkText}
            </a>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
