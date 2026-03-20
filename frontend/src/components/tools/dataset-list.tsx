"use client";

import { cn } from "@/lib/utils";
import type { Dataset } from "@/types/tools";

const categoryColors: Record<string, string> = {
  data_lake: "bg-green-100 text-green-800",
  library: "bg-purple-100 text-purple-800",
};

const categoryLabels: Record<string, string> = {
  data_lake: "Data Lake",
  library: "Library / Package",
};

export function DatasetList({ datasets }: { datasets: Dataset[] }) {
  if (datasets.length === 0) {
    return (
      <div className="text-center py-12 text-[var(--muted-foreground)]">
        No datasets found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--muted-foreground)]">
            <th className="px-4 py-2 font-medium">Name</th>
            <th className="px-4 py-2 font-medium">Category</th>
            <th className="px-4 py-2 font-medium">Description</th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((d) => (
            <tr
              key={`${d.category}-${d.name}`}
              className="border-b border-[var(--border)] hover:bg-[var(--muted)] transition-colors"
            >
              <td className="px-4 py-2 font-mono text-xs whitespace-nowrap">
                {d.name}
              </td>
              <td className="px-4 py-2">
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                    categoryColors[d.category] || "bg-gray-100 text-gray-700",
                  )}
                >
                  {categoryLabels[d.category] || d.category}
                </span>
              </td>
              <td className="px-4 py-2 text-[var(--muted-foreground)] max-w-lg">
                <span className="line-clamp-2">{d.description}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
