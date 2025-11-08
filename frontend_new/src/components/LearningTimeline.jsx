import React from "react";

export default function LearningTimeline({ plan }) {
  if (!plan || !plan.phases) return null;

  return (
    <div className="mt-6 p-4 border rounded-xl bg-slate-50">
      <h2 className="text-xl font-semibold mb-4 text-slate-800">
        📚 Learning Roadmap — {plan.occupation}
      </h2>

      <div className="space-y-6">
        {plan.phases.map((phase, index) => (
          <div
            key={index}
            className="relative border-l-4 border-blue-500 pl-4"
          >
            <div className="absolute -left-3 top-1 w-4 h-4 bg-blue-500 rounded-full"></div>

            <h3 className="text-lg font-medium">
              Phase {phase.phase_index}: {phase.skill}
            </h3>

            <div className="text-sm text-slate-600 italic mb=2">
              {phase.start} → {phase.end}
            </div>

            {/* Weekly milestones */}
            <ul className="list-disc ml-6 text-sm">
              {phase.weekly_milestones.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>

            {/* Recommended courses */}
            <div className="mt-2">
              <h4 className="font-medium text-sm">Recommended Courses:</h4>
              <ul className="ml-4 list-disc text-sm">
                {phase.courses?.map((course, i) => (
                  <li key={i}>
                    <a
                      href={course.url}
                      target="_blank"
                      className="text-blue-600 underline"
                    >
                      {course.title}
                    </a>{" "}
                    <span className="text-slate-500 text-xs">
                      ({course.platform})
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      {plan.capstone && (
        <div className="mt-6 border-t pt-4">
          <h3 className="text-lg font-semibold mb-1">🏆 Capstone Project</h3>
          <div className="font-medium">{plan.capstone.title}</div>
          <p className="text-sm text-slate-700">{plan.capstone.description}</p>
        </div>
      )}
    </div>
  );
}
