import type { ComponentProps } from "react";
import MarkdownRenderer from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

import { cn } from "cn";

const CITATION_SCHEME = "citation:";

// `[1]` -> a link to a fake `citation:1` URL, so react-markdown's own link
// parsing produces the node — no custom remark plugin needed. Skipped when
// already followed by `(` (an actual markdown link whose text happens to
// be a number, e.g. `[1](https://...)`) so real links are never touched.
// This runs over the whole raw string, fenced code blocks included — a
// literal `[1]` inside a code sample can turn into a citation link too;
// rare enough in practice, and harmless (a stray clickable badge) when it
// happens, not worth a full markdown-aware pass to prevent.
function linkifyCitations(text: string): string {
  return text.replace(/\[(\d+)\](?!\()/g, (match, n: string) => `[${match}](${CITATION_SCHEME}${n})`);
}

export function ChatMarkdown({
  content,
  onCitationClick,
  className,
}: {
  content: string;
  onCitationClick: (index: number) => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "prose-chat text-sm leading-relaxed text-foreground",
        "[&_p]:my-2 first:[&_p]:mt-0 last:[&_p]:mb-0",
        "[&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5",
        "[&_li]:my-0.5",
        "[&_h1]:mt-4 [&_h1]:mb-2 [&_h1]:text-base [&_h1]:font-semibold",
        "[&_h2]:mt-4 [&_h2]:mb-2 [&_h2]:text-sm [&_h2]:font-semibold",
        "[&_h3]:mt-3 [&_h3]:mb-1.5 [&_h3]:text-sm [&_h3]:font-semibold",
        "[&_strong]:font-semibold [&_a]:text-brand [&_a]:underline [&_a]:underline-offset-2",
        "[&_blockquote]:my-2 [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground",
        "[&_table]:my-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs",
        "[&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-medium",
        "[&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1",
        "[&_code]:rounded-sm [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.85em]",
        "[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-border [&_pre]:bg-muted/50 [&_pre]:p-3",
        "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-[0.85em]",
        className,
      )}
    >
      <MarkdownRenderer
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          a({ href, children, ...props }: ComponentProps<"a">) {
            if (href?.startsWith(CITATION_SCHEME)) {
              const index = Number(href.slice(CITATION_SCHEME.length));
              return (
                <button
                  type="button"
                  onClick={() => onCitationClick(index)}
                  className="mx-0.5 inline-flex size-4 items-center justify-center rounded-full bg-brand/15 align-text-top text-[0.7em] font-medium text-brand no-underline hover:bg-brand/25"
                  aria-label={`Source ${index}`}
                >
                  {index}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" {...props}>
                {children}
              </a>
            );
          },
        }}
      >
        {linkifyCitations(content)}
      </MarkdownRenderer>
    </div>
  );
}
