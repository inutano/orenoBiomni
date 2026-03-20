"use client";

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Code } from "lucide-react";

function detectLanguage(code: string): string {
  if (code.trimStart().startsWith("#!R") || code.trimStart().startsWith("# R "))
    return "r";
  if (
    code.trimStart().startsWith("#!BASH") ||
    code.trimStart().startsWith("# Bash") ||
    code.trimStart().startsWith("#!/bin/bash")
  )
    return "bash";
  return "python";
}

export function ExecuteBlock({ content }: { content: string }) {
  const lang = detectLanguage(content);

  return (
    <div className="rounded-lg overflow-hidden text-sm border border-[var(--border)]">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#282c34] text-gray-400 text-xs">
        <Code size={12} />
        <span>{lang}</span>
      </div>
      <SyntaxHighlighter
        language={lang}
        style={oneDark}
        customStyle={{ margin: 0, fontSize: "0.8rem" }}
      >
        {content}
      </SyntaxHighlighter>
    </div>
  );
}
