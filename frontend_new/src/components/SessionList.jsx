import React from "react";
import { Trash2 } from "lucide-react";

export default function SessionList({ sessions, activeUserId, onSelect, onDelete }) {
  return (
    <div className="overflow-y-auto h-[calc(100vh-60px)]">
      {sessions.map((s) => (
        <div
          key={s.user_id}
          onClick={() => onSelect(s.user_id)}
          className={`flex items-center justify-between px-4 py-3 border-b cursor-pointer 
            hover:bg-gray-100 transition ${
              activeUserId === s.user_id ? "bg-indigo-50" : ""
            }`}
        >
          {/* LEFT: filename + user circle */}
          <div className="flex items-center gap-3 overflow-hidden flex-1">
            <div className="w-9 h-9 rounded-full bg-indigo-600 text-white flex items-center justify-center text-sm font-semibold">
              {s.fileName?.[0]?.toUpperCase() || "U"}
            </div>

            <div className="flex flex-col overflow-hidden">
              <span
                className="text-sm font-medium truncate max-w-[160px]"
                title={s.fileName}
              >
                {s.fileName}
              </span>
              <span className="text-xs text-gray-500 truncate max-w-[160px]">
                {s.parsed_resume?.full_name || "Unknown User"}
              </span>
            </div>
          </div>

          {/* RIGHT: Delete icon */}
          <Trash2
            size={18}
            className="text-gray-400 hover:text-red-500 ml-3 flex-shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(s.user_id);
            }}
          />
        </div>
      ))}
    </div>
  );
}
