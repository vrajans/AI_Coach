import React from "react";

export default function EngineInspector({ engineContext, sourceDocs }) {
  if (!engineContext) return null;

  // Ensure safe object
  let ctx = engineContext;
  if (typeof ctx === "string") {
    try {
      ctx = JSON.parse(ctx);
    } catch {
      // fallback to raw string
      return (
        <div className="bg-gray-50 p-3 rounded border text-sm">
          <strong>Engine Context:</strong>
          <p className="mt-1 whitespace-pre-line">{ctx}</p>
        </div>
      );
    }
  }

  // Safely extract flattened fields
  const domain = ctx.domain || "Not detected";
  const primOcc = ctx.primary_occupation || ctx.occupation || "Not detected";
  const canonical = ctx?.occupation_meta?.canonical || null;

  const gaps = Array.isArray(ctx.skill_gaps) && ctx.skill_gaps.length > 0
    ? ctx.skill_gaps.join(", ")
    : "None";

  const learn = ctx?.learning_plan?.summary || null;
  const salary = ctx.salary || null;

  return (
    <div className="bg-gray-50 p-4 rounded border text-sm leading-relaxed">

      <div>
        <strong>Domain:</strong> {domain}
      </div>

      <div>
        <strong>Occupation:</strong> {primOcc}
      </div>

      {canonical && (
        <div>
          <strong>Canonical Role:</strong> {canonical}
        </div>
      )}

      <div>
        <strong>Skill Gaps:</strong> {gaps}
      </div>

      {learn && (
        <div className="mt-1">
          <strong>Learning Plan:</strong>
          <div className="mt-1 bg-white p-2 rounded border text-xs">
            {learn}
          </div>
        </div>
      )}

      {salary && (
        <div className="mt-1">
          <strong>Salary Estimate:</strong> {salary}
        </div>
      )}

      {sourceDocs?.length > 0 && (
        <div className="mt-2">
          <strong>Sources:</strong>
          <ul className="list-disc ml-4 text-xs">
            {sourceDocs.map((d, i) => (
              <li key={i}>{d.page_content?.slice(0, 120)}...</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
