import React from "react";

export default function ResumeSidebar({ parsed_resume, onClose }) {
  if (!parsed_resume) {
    return (
      <div className="p-4 text-gray-500">
        No resume parsed.
        <button onClick={onClose} className="text-xs text-red-500 ml-2">
          Close
        </button>
      </div>
    );
  }

  return (
    <div className="p-5 overflow-y-auto h-full text-sm">
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-semibold text-lg">Resume Summary</h2>
        <button onClick={onClose} className="text-xs text-red-500">
          Close
        </button>
      </div>

      {/* Full name */}
      <p className="text-gray-900 font-medium text-base mb-1">
        {parsed_resume.full_name || "Unknown"}
      </p>

      {/* Email */}
      <p className="text-gray-500 mb-4">{parsed_resume.email || ""}</p>

      {/* SKILLS */}
      <div className="mb-5">
        <h3 className="font-semibold text-gray-700 mb-1">Skills</h3>
        {parsed_resume.skills && parsed_resume.skills.length > 0 ? (
          <ul className="list-disc ml-5 text-gray-700">
            {parsed_resume.skills.map((sk, i) => (
              <li key={i}>{sk}</li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-400">No skills parsed.</p>
        )}
      </div>

      {/* EXPERIENCE */}
      <div className="mb-5">
        <h3 className="font-semibold text-gray-700 mb-1">Experience</h3>
        {parsed_resume.experience && parsed_resume.experience.length > 0 ? (
          <div className="space-y-3">
            {parsed_resume.experience.map((exp, i) => (
              <div key={i} className="border p-3 rounded bg-gray-50">
                <p className="font-semibold text-gray-800">{exp.role}</p>
                <p className="text-gray-500">{exp.company}</p>
                {exp.bullets?.length > 0 && (
                  <ul className="ml-5 list-disc text-gray-700">
                    {exp.bullets.map((b, j) => (
                      <li key={j}>{b}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">No experience parsed.</p>
        )}
      </div>

      {/* EDUCATION */}
      <div className="mb-5">
        <h3 className="font-semibold text-gray-700 mb-1">Education</h3>
        {parsed_resume.education && parsed_resume.education.length > 0 ? (
          <ul className="list-disc ml-5 text-gray-700">
            {parsed_resume.education.map((ed, i) => (
              <li key={i}>{ed}</li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-400">No education parsed.</p>
        )}
      </div>
    </div>
  );
}
