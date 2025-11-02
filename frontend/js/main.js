// Auto-detect API base URL
const API_URL =
  window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : window.location.origin;

let userId = localStorage.getItem("userId") || null;
let chatHistory = JSON.parse(localStorage.getItem("chatHistory") || "[]");

const chatContainer = document.getElementById("chatContainer");
const input = document.getElementById("userInput");
const chatCard = document.getElementById("chatCard");
const uploadStatus = document.getElementById("uploadStatus");

// Restore chat history on reload
chatHistory.forEach(({ sender, message }) => appendMessage(sender, message));
if (userId) chatCard.style.display = "block";

document.getElementById("uploadBtn").addEventListener("click", uploadResume);
document.getElementById("sendBtn").addEventListener("click", sendMessage);
document.getElementById("clearChat").addEventListener("click", clearChat);
input.addEventListener("keydown", handleKey);

async function uploadResume() {
  const fileInput = document.getElementById("resumeFile");
  const domainSelect = document.getElementById("domainSelect");
  const domain = domainSelect ? domainSelect.value : "";

  if (!fileInput.files.length) {
    uploadStatus.innerText = "⚠️ Please select a file.";
    return;
  }

  const uploadBtn = document.getElementById("uploadBtn");
  uploadBtn.disabled = true;
  uploadStatus.innerText = "⏳ Uploading and analyzing...";

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  if (domain) formData.append("domain", domain);

  try {
    const resp = await fetch(`${API_URL}/upload_resume/`, {
      method: "POST",
      body: formData,
    });

    const data = await resp.json();
    uploadBtn.disabled = false;

    if (resp.ok) {
      userId = data.user_id;
      localStorage.setItem("userId", userId);
      uploadStatus.innerText = "✅ Resume processed successfully!";
      chatCard.style.display = "block";
      document.getElementById("uploadCard").style.display = "none";
    } else {
      uploadStatus.innerText = "❌ Failed to process resume.";
    }
  } catch (err) {
    uploadBtn.disabled = false;
    uploadStatus.innerText = "❌ Error uploading resume.";
    console.error(err);
  }
}

function handleKey(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    sendMessage();
  }
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message || !userId) return;

  appendMessage("user", message);
  saveMessage("user", message);
  input.value = "";

  const typing = document.createElement("div");
  typing.classList.add("typing");
  typing.innerText = "AI is typing...";
  chatContainer.appendChild(typing);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  try {
    const resp = await fetch(`${API_URL}/chat/${userId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    const data = await resp.json();
    typing.remove();

    const answer = data.answer || "⚠️ Sorry, I couldn’t process that.";
    appendMessage("bot", answer);
    saveMessage("bot", answer);
  } catch (err) {
    typing.remove();
    appendMessage("bot", "❌ Error connecting to server.");
    console.error(err);
  }
}

function appendMessage(sender, message) {
  const msg = document.createElement("div");
  msg.classList.add("message", sender);

  const bubble = document.createElement("div");
  bubble.classList.add("bubble");
  bubble.innerText = message;

  msg.appendChild(bubble);
  chatContainer.appendChild(msg);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function saveMessage(sender, message) {
  chatHistory.push({ sender, message });
  localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
}

function clearChat() {
  localStorage.removeItem("chatHistory");
  chatHistory = [];
  chatContainer.innerHTML = "";
}