const questionInput = document.getElementById("question");
const askButton = document.getElementById("askButton");
const statusEl = document.getElementById("status");
const answerSection = document.getElementById("answerSection");
const evidenceSection = document.getElementById("evidenceSection");
const answerEl = document.getElementById("answer");
const evidenceEl = document.getElementById("evidence");
const modelBadge = document.getElementById("modelBadge");
const healthEl = document.getElementById("health");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderEvidence(items) {
  evidenceEl.innerHTML = items.map(item => `
    <article class="evidence-item">
      <div class="evidence-top">
        <span class="rank">Evidence #${item.rank}</span>
        <span class="similarity">Similarity: ${item.similarity}</span>
      </div>
      <div class="meta">
        <div><b>Document:</b> ${escapeHtml(item.document_name)}</div>
        <div><b>Page:</b> ${escapeHtml(item.page_number)}</div>
        <div><b>Section:</b> ${escapeHtml(item.section)}</div>
        <div><b>Chunk ID:</b> ${escapeHtml(item.chunk_id)}</div>
        <div><b>Source:</b> ${escapeHtml(item.source)}</div>
        <div><b>Version:</b> ${escapeHtml(item.version)}</div>
      </div>
      <div class="evidence-text">${escapeHtml(item.text)}</div>
    </article>
  `).join("");
}

async function ask() {
  const question = questionInput.value.trim();
  if (!question) {
    statusEl.textContent = "Please enter a question.";
    questionInput.focus();
    return;
  }

  askButton.disabled = true;
  statusEl.textContent = "Retrieving evidence and generating answer…";
  answerSection.classList.add("hidden");
  evidenceSection.classList.add("hidden");

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 4 })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Request failed.");

    answerEl.textContent = data.answer;
    modelBadge.textContent = data.model;
    renderEvidence(data.evidence);
    answerSection.classList.remove("hidden");
    evidenceSection.classList.remove("hidden");
    statusEl.textContent = "Answer ready.";
  } catch (error) {
    statusEl.textContent = error.message;
  } finally {
    askButton.disabled = false;
  }
}

askButton.addEventListener("click", ask);
questionInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") ask();
});

document.querySelectorAll(".example").forEach(button => {
  button.addEventListener("click", () => {
    questionInput.value = button.textContent;
    questionInput.focus();
  });
});

fetch("/api/health")
  .then(response => response.json())
  .then(data => { healthEl.textContent = `Backend: ${data.status}`; })
  .catch(() => { healthEl.textContent = "Backend: unavailable"; });
