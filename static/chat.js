/**
 * frAInk chat — vanilla JS, streaming SSE
 * Handles multi-turn conversation with the /api/chat endpoint.
 */

const messagesEl = document.getElementById("chatMessages");
const inputEl    = document.getElementById("chatInput");
const sendBtn    = document.getElementById("sendBtn");

// In-memory conversation history (multi-turn context)
const history = [];
let streaming  = false;

// ---------------------------------------------------------------------------
// Auto-grow textarea
// ---------------------------------------------------------------------------

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 180) + "px";
});

// ---------------------------------------------------------------------------
// Submit on Enter, Shift+Enter for newline
// ---------------------------------------------------------------------------

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (!streaming) sendMessage();
  }
});

sendBtn.addEventListener("click", () => {
  if (!streaming) sendMessage();
});

// ---------------------------------------------------------------------------
// Send message
// ---------------------------------------------------------------------------

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  // Add user message to UI and history
  appendMessage("user", text);
  history.push({ role: "user", content: text });

  // Reset input
  inputEl.value = "";
  inputEl.style.height = "auto";

  // Start frAInk response
  await streamResponse();
}

// ---------------------------------------------------------------------------
// Stream response from /api/chat
// ---------------------------------------------------------------------------

async function streamResponse() {
  streaming = true;
  sendBtn.disabled = true;
  sendBtn.style.opacity = "0.4";

  // Create empty frAInk message bubble
  const msgEl = createMessageEl("fraink");
  const contentEl = msgEl.querySelector(".msg-content");
  messagesEl.appendChild(msgEl);
  scrollToBottom();

  // Show typing indicator
  const typingEl = document.createElement("span");
  typingEl.className = "typing-indicator";
  typingEl.textContent = "▍";
  contentEl.appendChild(typingEl);

  let fullText = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") continue;

        try {
          const data = JSON.parse(payload);
          if (data.error) {
            throw new Error(data.error);
          }
          if (data.text) {
            fullText += data.text;
            // Remove typing indicator, render text
            typingEl.remove();
            contentEl.innerHTML = formatMessage(fullText);
            // Re-add blinking cursor
            const cursor = document.createElement("span");
            cursor.className = "typing-indicator";
            cursor.textContent = "▍";
            contentEl.appendChild(cursor);
            scrollToBottom();
          }
        } catch (parseErr) {
          // Skip malformed lines
        }
      }
    }

    // Remove cursor, finalize
    contentEl.innerHTML = formatMessage(fullText);

    // Add to history
    history.push({ role: "assistant", content: fullText });

  } catch (err) {
    contentEl.innerHTML = `<p style="color: #f85149;">Something went wrong: ${escapeHtml(err.message)}</p>`;
  }

  streaming = false;
  sendBtn.disabled = false;
  sendBtn.style.opacity = "1";
  scrollToBottom();
  inputEl.focus();
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function appendMessage(role, text) {
  const msgEl = createMessageEl(role);
  msgEl.querySelector(".msg-content").innerHTML = formatMessage(text);
  messagesEl.appendChild(msgEl);
  scrollToBottom();
}

function createMessageEl(role) {
  const div = document.createElement("div");
  div.className = `msg msg-${role}`;
  const content = document.createElement("div");
  content.className = "msg-content";
  div.appendChild(content);
  return div;
}

/**
 * Format plain text to HTML:
 * - Blank lines → paragraph breaks
 * - Preserve inline content
 */
function formatMessage(text) {
  const escaped = escapeHtml(text);
  const paragraphs = escaped.split(/\n\s*\n/);
  return paragraphs
    .map(p => {
      const lines = p.split("\n").join("<br>");
      return `<p>${lines}</p>`;
    })
    .join("");
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
