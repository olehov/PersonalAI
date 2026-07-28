async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : { error: await response.text() };

  if (!response.ok) {
    const message =
      (typeof payload.error === "string" && payload.error.trim()) ||
      (typeof payload.message === "string" && payload.message.trim()) ||
      (typeof payload.detail === "string" && payload.detail.trim()) ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

export function reloadVault() {
  return requestJson("/api/reload", { method: "POST", body: "{}" });
}

export function listModels() {
  return requestJson("/api/models", { method: "GET" });
}

export function autoRoute({ prompt, chatHistory = [], title = "", directory = "", targetDir = "Inbox" }) {
  return requestJson("/api/auto-route", {
    method: "POST",
    body: JSON.stringify({
      prompt,
      chat_history: chatHistory,
      title,
      directory,
      target_dir: targetDir,
    }),
  });
}

export function askQuestion({ question, model, scopeText, chatHistory = [], reasoningMode = "auto" }) {
  return requestJson("/api/ask", {
    method: "POST",
    body: JSON.stringify({
      question,
      model,
      scope_text: scopeText,
      chat_history: chatHistory,
      reasoning_mode: reasoningMode,
    }),
  });
}

export function autoRunRequest({
  prompt,
  model,
  scopeText,
  chatHistory = [],
  reasoningMode = "auto",
  discussionPreset = "heavy_synthesis",
  title = "",
  directory = "",
  targetDir = "Inbox",
}) {
  return requestJson("/api/auto-run", {
    method: "POST",
    body: JSON.stringify({
      prompt,
      model,
      scope_text: scopeText,
      chat_history: chatHistory,
      reasoning_mode: reasoningMode,
      discussion_preset: discussionPreset,
      title,
      directory,
      target_dir: targetDir,
    }),
  });
}

export function scopeImplementation({
  requestText,
  model,
  scopeText,
  chatHistory = [],
  reasoningMode = "auto",
}) {
  return requestJson("/api/implementation-scope", {
    method: "POST",
    body: JSON.stringify({
      request_text: requestText,
      model,
      scope_text: scopeText,
      chat_history: chatHistory,
      reasoning_mode: reasoningMode,
    }),
  });
}

export function runAgentRuntime({
  requestText,
  model,
  scopeText,
  chatHistory = [],
  reasoningMode = "auto",
  discussionPreset = "heavy_synthesis",
}) {
  return requestJson("/api/agent-runtime", {
    method: "POST",
    body: JSON.stringify({
      request_text: requestText,
      model,
      scope_text: scopeText,
      chat_history: chatHistory,
      reasoning_mode: reasoningMode,
      discussion_preset: discussionPreset,
    }),
  });
}

export function updateAgentTaskPlan({ entryId, taskPlan }) {
  return requestJson("/api/agent-task-plan", {
    method: "POST",
    body: JSON.stringify({
      entry_id: entryId,
      task_plan: taskPlan,
    }),
  });
}

export function listAskHistory(limit) {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestJson(`/api/ask-history?${params.toString()}`, { method: "GET" });
}

export function listAgentHistory(limit) {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestJson(`/api/agent-history?${params.toString()}`, { method: "GET" });
}

export function listBenchmarkHistory(limit) {
  const params = new URLSearchParams({ limit: String(limit) });
  return requestJson(`/api/benchmark-history?${params.toString()}`, { method: "GET" });
}

export function getHistoryOverview() {
  return requestJson("/api/history-overview", { method: "GET" });
}

export function analyzeDirectory({ directory }) {
  return requestJson("/api/analyze-dir", {
    method: "POST",
    body: JSON.stringify({ directory }),
  });
}

export function draftNote({ title, instruction, model, targetDir, scopeText }) {
  return requestJson("/api/draft-note", {
    method: "POST",
    body: JSON.stringify({
      title,
      instruction,
      model,
      target_dir: targetDir,
      scope_text: scopeText,
    }),
  });
}
