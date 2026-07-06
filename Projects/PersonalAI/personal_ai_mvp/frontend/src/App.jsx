import { useEffect, useMemo, useState } from "react";

import {
  analyzeDirectory,
  askQuestion,
  autoRunRequest,
  draftNote,
  getHistoryOverview,
  listAgentHistory,
  listAskHistory,
  listModels,
  reloadVault,
  runAgentRuntime,
  scopeImplementation,
  updateAgentTaskPlan,
} from "./api.js";

const DEFAULT_MODEL = "gemma:latest";
const CHAT_STORAGE_KEY = "personal-ai-chat-sessions";
const HISTORY_LIMIT = 12;

const workflowOptions = [
  { value: "auto", label: "Auto", needsModel: true },
  { value: "ask", label: "Ask", needsModel: true },
  { value: "implementation", label: "Scope", needsModel: true },
  { value: "agent", label: "Agent", needsModel: true },
  { value: "analyze", label: "Analyze", needsModel: false },
  { value: "draft", label: "Draft", needsModel: true },
];

const discussionPresetOptions = [
  { value: "heavy_synthesis", label: "Heavy Synthesis" },
  { value: "coder_critic", label: "Coder Critic" },
  { value: "fast", label: "Fast Debate" },
];

const discussionPresetLabels = Object.fromEntries(
  discussionPresetOptions.map((option) => [option.value, option.label]),
);

const composerDefaults = {
  workflow: "auto",
  reasoningMode: "auto",
  discussionPreset: "heavy_synthesis",
  prompt: "",
  model: DEFAULT_MODEL,
  scopeText: "Projects, Languages/C",
  directory: "Languages/C",
  title: "",
  targetDir: "Inbox",
};

function App() {
  const [modelOptions, setModelOptions] = useState([DEFAULT_MODEL]);
  const [status, setStatus] = useState({
    type: "info",
    message: "Connecting to PersonalAI backend...",
  });
  const [chatSessions, setChatSessions] = useState(() => loadStoredChats());
  const [activeChatId, setActiveChatId] = useState(() => loadStoredChats()[0]?.id ?? "");
  const [composer, setComposer] = useState(composerDefaults);
  const [busy, setBusy] = useState(false);
  const [historyEntries, setHistoryEntries] = useState([]);
  const [agentHistoryEntries, setAgentHistoryEntries] = useState([]);
  const [historyOverview, setHistoryOverview] = useState({
    ask: 0,
    agent: 0,
    benchmark: 0,
  });

  const activeChat = useMemo(
    () => chatSessions.find((chat) => chat.id === activeChatId) ?? null,
    [activeChatId, chatSessions],
  );

  useEffect(() => {
    if (chatSessions.length === 0) {
      const firstChat = createChatSession();
      setChatSessions([firstChat]);
      setActiveChatId(firstChat.id);
      return;
    }
    if (!activeChatId || !chatSessions.some((chat) => chat.id === activeChatId)) {
      setActiveChatId(chatSessions[0].id);
    }
  }, [activeChatId, chatSessions]);

  useEffect(() => {
    window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(chatSessions));
  }, [chatSessions]);

  useEffect(() => {
    loadModelsAndHistory();
  }, []);

  async function loadModelsAndHistory() {
    await Promise.all([loadModels(), refreshHistory(), refreshAgentHistory(), refreshHistoryOverview()]);
  }

  async function loadModels() {
    try {
      const payload = await listModels();
      const models = payload.models?.length ? payload.models : [payload.default_model ?? DEFAULT_MODEL];
      setModelOptions(models);
      setComposer((current) => ({
        ...current,
        model: models.includes(current.model) ? current.model : models[0],
      }));
      setStatus({
        type: "info",
        message: "Models loaded.",
      });
    } catch (error) {
      setModelOptions([DEFAULT_MODEL]);
      setStatus({
        type: "error",
        message: error.message,
      });
    }
  }

  async function refreshHistory() {
    try {
      const payload = await listAskHistory(HISTORY_LIMIT);
      setHistoryEntries(payload.entries ?? []);
    } catch (error) {
      setStatus({
        type: "error",
        message: error.message,
      });
    }
  }

  async function refreshAgentHistory() {
    try {
      const payload = await listAgentHistory(HISTORY_LIMIT);
      setAgentHistoryEntries(payload.entries ?? []);
    } catch (error) {
      setStatus({
        type: "error",
        message: error.message,
      });
    }
  }

  async function refreshHistoryOverview() {
    try {
      const payload = await getHistoryOverview();
      setHistoryOverview(payload.streams ?? { ask: 0, agent: 0, benchmark: 0 });
    } catch (error) {
      setStatus({
        type: "error",
        message: error.message,
      });
    }
  }

  function handleNewChat() {
    const nextChat = createChatSession();
    setChatSessions((current) => [nextChat, ...current]);
    setActiveChatId(nextChat.id);
    setComposer((current) => ({
      ...composerDefaults,
      model: current.model,
    }));
  }

  function handleSelectChat(chatId) {
    setActiveChatId(chatId);
  }

  function handleDeleteChat(chatId) {
    setChatSessions((current) => current.filter((chat) => chat.id !== chatId));
  }

  async function handleReloadVault() {
    setBusy(true);
    try {
      await reloadVault();
      await Promise.all([refreshHistory(), refreshAgentHistory(), refreshHistoryOverview()]);
      setStatus({
        type: "info",
        message: "Vault index reloaded.",
      });
    } catch (error) {
      setStatus({
        type: "error",
        message: error.message,
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!activeChat || !composer.prompt.trim()) {
      return;
    }

    const workflow = workflowOptions.find((option) => option.value === composer.workflow);
    const userMessage = buildUserMessage(composer, workflow?.label ?? "Ask");
    const chatHistory = buildConversationHistory(activeChat.messages);
    appendMessage(activeChat.id, userMessage);
    setBusy(true);

    try {
      const execution = await runWorkflow(composer, chatHistory);
      appendMessage(
        activeChat.id,
        buildAssistantMessage({
          workflow: execution.workflow,
          model: composer.model,
          reasoningMode: execution.reasoningMode,
          result: execution.result,
          route: execution.route ?? null,
        }),
      );
      setChatSessions((current) =>
        current.map((chat) =>
          chat.id === activeChat.id
            ? {
                ...chat,
                title: deriveChatTitle(chat.title, userMessage.text),
              }
            : chat,
        ),
      );
      setComposer((current) => ({
        ...current,
        prompt: "",
        title: current.workflow === "draft" ? current.title : "",
      }));
      await refreshHistory();
      await refreshAgentHistory();
      await refreshHistoryOverview();
      setStatus({
        type: "info",
        message: `${workflow?.label ?? "Request"} completed.`,
      });
    } catch (error) {
      appendMessage(
        activeChat.id,
        buildSystemMessage(`Request failed: ${error.message}`),
      );
      setStatus({
        type: "error",
        message: error.message,
      });
    } finally {
      setBusy(false);
    }
  }

  async function runWorkflow(currentComposer, chatHistory) {
    if (currentComposer.workflow === "auto") {
      const payload = await autoRunRequest({
        prompt: currentComposer.prompt,
        model: currentComposer.model,
        scopeText: currentComposer.scopeText,
        chatHistory,
        reasoningMode: currentComposer.reasoningMode,
        discussionPreset: currentComposer.discussionPreset,
        title: currentComposer.title,
        directory: currentComposer.directory,
        targetDir: currentComposer.targetDir,
      });
      return {
        workflow: payload.route?.workflow ?? "ask",
        reasoningMode: payload.reasoning_mode ?? payload.route?.reasoning_mode ?? "standard",
        result: payload.result,
        route: payload.route ?? null,
      };
    }

    if (currentComposer.workflow === "ask") {
      const payload = await askQuestion({
        question: currentComposer.prompt,
        model: currentComposer.model,
        scopeText: currentComposer.scopeText,
        chatHistory,
        reasoningMode: currentComposer.reasoningMode,
      });
      return {
        workflow: "ask",
        reasoningMode: resolveManualReasoningMode(currentComposer.reasoningMode),
        result: payload.result,
      };
    }

    if (currentComposer.workflow === "implementation") {
      const payload = await scopeImplementation({
        requestText: currentComposer.prompt,
        model: currentComposer.model,
        scopeText: currentComposer.scopeText,
        chatHistory,
        reasoningMode: currentComposer.reasoningMode,
      });
      return {
        workflow: "implementation",
        reasoningMode: resolveManualReasoningMode(currentComposer.reasoningMode),
        result: payload.result,
      };
    }

    if (currentComposer.workflow === "agent") {
      const payload = await runAgentRuntime({
        requestText: currentComposer.prompt,
        model: currentComposer.model,
        scopeText: currentComposer.scopeText,
        chatHistory,
        reasoningMode: currentComposer.reasoningMode,
        discussionPreset: currentComposer.discussionPreset,
      });
      return {
        workflow: "agent",
        reasoningMode: resolveManualReasoningMode(currentComposer.reasoningMode),
        result: payload.result,
      };
    }

    if (currentComposer.workflow === "analyze") {
      const payload = await analyzeDirectory({
        directory: currentComposer.directory,
      });
      return { workflow: "analyze", reasoningMode: "standard", result: payload.result };
    }

    const payload = await draftNote({
      title: currentComposer.title,
      instruction: currentComposer.prompt,
      model: currentComposer.model,
      targetDir: currentComposer.targetDir,
      scopeText: currentComposer.scopeText,
    });
    return { workflow: "draft", reasoningMode: "standard", result: payload.result };
  }

  function appendMessage(chatId, message) {
    setChatSessions((current) =>
      current.map((chat) =>
        chat.id === chatId
          ? {
              ...chat,
              updatedAt: new Date().toISOString(),
              messages: [...chat.messages, message],
            }
          : chat,
      ),
    );
  }

  async function updateAgentTaskPlanState(chatId, messageId, entryIndex, action) {
    let nextTaskPlan = null;
    let historyEntryId = null;

    setChatSessions((current) =>
      current.map((chat) => {
        if (chat.id !== chatId) {
          return chat;
        }
        return {
          ...chat,
          updatedAt: new Date().toISOString(),
          messages: chat.messages.map((message) => {
            if (message.id !== messageId || message.kind !== "agent" || !message.payload?.taskPlan) {
              return message;
            }
            nextTaskPlan = updateTaskPlanState(message.payload.taskPlan, entryIndex, action);
            historyEntryId = message.payload.historyEntryId ?? null;
            return {
              ...message,
              payload: {
                ...message.payload,
                taskPlan: nextTaskPlan,
              },
            };
          }),
        };
      }),
    );

    if (!nextTaskPlan || !historyEntryId) {
      return;
    }

    try {
      await updateAgentTaskPlan({
        entryId: historyEntryId,
        taskPlan: serializeTaskPlanForApi(nextTaskPlan),
      });
    } catch (error) {
      setStatus({
        type: "error",
        message: `Task plan update failed: ${error.message}`,
      });
    }
  }

  function importHistoryEntry(entry) {
    const importedChat = {
      id: crypto.randomUUID(),
      title: truncateText(entry.question, 42) || "Imported run",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [
        {
          id: crypto.randomUUID(),
          role: "user",
          kind: "history-import",
          label: "Imported Question",
          text: entry.question,
          meta: `${entry.model} | ${entry.task_mode} | ${entry.created_at}`,
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "history-answer",
          label: "Imported Answer",
          text: entry.answer_text,
          meta: `latency ${entry.latency_ms ?? "n/a"} ms`,
        },
      ],
    };

    setChatSessions((current) => [importedChat, ...current]);
    setActiveChatId(importedChat.id);
    setStatus({
      type: "info",
      message: "History entry imported as a chat.",
    });
  }

  function importAgentHistoryEntry(entry) {
    const result = entry.artifact_payload ?? {};
    const importedChat = {
      id: crypto.randomUUID(),
      title: truncateText(entry.normalized_goal || entry.request_text, 42) || "Imported agent run",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [
        {
          id: crypto.randomUUID(),
          role: "user",
          kind: "agent-history-import",
          label: "Imported Agent Request",
          text: entry.request_text,
          meta: `${entry.model} | ${entry.task_mode} | ${entry.created_at}`,
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "agent",
          label: "Imported Agent Run",
          meta: `status ${entry.status} | latency ${entry.latency_ms ?? "n/a"} ms`,
          payload: normalizeResult("agent", { ...result, history_entry_id: entry.entry_id }),
        },
      ],
    };

    setChatSessions((current) => [importedChat, ...current]);
    setActiveChatId(importedChat.id);
    setStatus({
      type: "info",
      message: "Agent history entry imported as a chat.",
    });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-top">
          <div>
            <p className="sidebar-kicker">PersonalAI</p>
            <h1>Chats</h1>
          </div>
          <button className="primary-button" onClick={handleNewChat} type="button">
            New Chat
          </button>
        </div>

        <div className="chat-list">
          {chatSessions.map((chat) => (
            <button
              className={`chat-item${chat.id === activeChatId ? " active" : ""}`}
              key={chat.id}
              onClick={() => handleSelectChat(chat.id)}
              type="button"
            >
              <span className="chat-item-title">{chat.title}</span>
              <span className="chat-item-meta">
                {formatTimestamp(chat.updatedAt)} | {chat.messages.length} msgs
              </span>
              <span
                aria-label={`Delete ${chat.title}`}
                className="chat-item-delete"
                onClick={(event) => {
                  event.stopPropagation();
                  handleDeleteChat(chat.id);
                }}
                role="button"
                tabIndex={0}
              >
                ×
              </span>
            </button>
          ))}
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <h2>Saved Runs</h2>
            <button
              className="text-button"
              onClick={() => Promise.all([refreshHistory(), refreshAgentHistory()])}
              type="button"
            >
              Refresh
            </button>
          </div>
          <div className="history-stack">
            <div className="history-group">
              <p className="history-group-title">Ask / Scope ({historyOverview.ask})</p>
              {historyEntries.length === 0 ? (
                <p className="muted-copy">No saved ask runs yet.</p>
              ) : (
                historyEntries.map((entry) => (
                  <div className="history-card" key={`history-${entry.entry_id}`}>
                    <p className="history-card-title">{truncateText(entry.question, 58)}</p>
                    <p className="history-card-meta">
                      {entry.model} | {entry.task_mode}
                    </p>
                    <button
                      className="ghost-button compact"
                      onClick={() => importHistoryEntry(entry)}
                      type="button"
                    >
                      Open as Chat
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="history-group">
              <p className="history-group-title">Agent Runs ({historyOverview.agent})</p>
              {agentHistoryEntries.length === 0 ? (
                <p className="muted-copy">No saved agent runs yet.</p>
              ) : (
                agentHistoryEntries.map((entry) => (
                  <div className="history-card" key={`agent-${entry.entry_id}`}>
                    <p className="history-card-title">
                      {truncateText(entry.normalized_goal || entry.request_text, 58)}
                    </p>
                    <p className="history-card-meta">
                      {entry.model} | {entry.artifact_payload?.discussion_preset ?? "custom"} | {entry.status}
                    </p>
                    <button
                      className="ghost-button compact"
                      onClick={() => importAgentHistoryEntry(entry)}
                      type="button"
                    >
                      Open as Chat
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </aside>

      <main className="chat-layout">
        <header className="topbar">
          <div>
            <p className="sidebar-kicker">Local-First Developer Assistant</p>
            <h2>{activeChat?.title ?? "Chat"}</h2>
          </div>
          <div className="topbar-actions">
            <span className="model-pill">{composer.model}</span>
            <button className="ghost-button" onClick={handleReloadVault} disabled={busy} type="button">
              Reload Vault
            </button>
          </div>
        </header>

        <StatusBanner type={status.type} message={status.message} />

        <section className="message-thread">
          {activeChat?.messages.length ? (
            activeChat.messages.map((message) => (
              <MessageBubble
                key={message.id}
                chatId={activeChat.id}
                message={message}
                onTaskPlanUpdate={updateAgentTaskPlanState}
              />
            ))
          ) : (
            <EmptyState />
          )}
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          <div className="composer-toolbar">
            <Field
              label="Mode"
              value={composer.workflow}
              onChange={(value) => setComposer((current) => ({ ...current, workflow: value }))}
              options={workflowOptions.map((option) => option.value)}
              labels={Object.fromEntries(workflowOptions.map((option) => [option.value, option.label]))}
            />
            {workflowOptions.find((option) => option.value === composer.workflow)?.needsModel ? (
              <Field
                label="Model"
                value={composer.model}
                onChange={(value) => setComposer((current) => ({ ...current, model: value }))}
                options={modelOptions}
              />
            ) : null}
            {composer.workflow !== "analyze" && composer.workflow !== "draft" ? (
              <Field
                label="Reasoning"
                value={composer.reasoningMode}
                onChange={(value) => setComposer((current) => ({ ...current, reasoningMode: value }))}
                options={["auto", "standard", "high"]}
                labels={{ auto: "Auto", standard: "Standard", high: "High" }}
              />
            ) : null}
            {(composer.workflow === "auto" || composer.workflow === "agent") ? (
              <Field
                label="Role Preset"
                value={composer.discussionPreset}
                onChange={(value) => setComposer((current) => ({ ...current, discussionPreset: value }))}
                options={discussionPresetOptions.map((option) => option.value)}
                labels={discussionPresetLabels}
              />
            ) : null}
            {composer.workflow === "analyze" ? (
              <Field
                label="Directory"
                value={composer.directory}
                onChange={(value) => setComposer((current) => ({ ...current, directory: value }))}
                placeholder="Languages/C"
              />
            ) : null}
            {composer.workflow === "draft" ? (
              <>
                <Field
                  label="Title"
                  value={composer.title}
                  onChange={(value) => setComposer((current) => ({ ...current, title: value }))}
                  placeholder="Shell Parser Architecture"
                />
                <Field
                  label="Target"
                  value={composer.targetDir}
                  onChange={(value) => setComposer((current) => ({ ...current, targetDir: value }))}
                  placeholder="Inbox"
                />
              </>
            ) : null}
          </div>

          {composer.workflow !== "analyze" ? (
            <input
              className="scope-input"
              value={composer.scopeText}
              onChange={(event) =>
                setComposer((current) => ({ ...current, scopeText: event.target.value }))
              }
              placeholder="Scope dirs: Projects, Languages/C"
            />
          ) : null}

          <textarea
            value={composer.prompt}
            onChange={(event) =>
              setComposer((current) => ({ ...current, prompt: event.target.value }))
            }
            placeholder={placeholderForWorkflow(composer.workflow)}
          />

          <div className="composer-footer">
            <p className="muted-copy">
              {composer.workflow === "ask"
                ? "Grounded coding answer against your vault and local model."
                : composer.workflow === "auto"
                  ? "Let the backend choose the best workflow, while keeping manual modes available as override."
                  : composer.workflow === "implementation"
                  ? "Break a big task into concrete implementation slices."
                  : composer.workflow === "agent"
                    ? "Run a planning-oriented agent runtime with grounded steps and explicit limits."
                  : composer.workflow === "analyze"
                    ? "Inspect a directory and surface gaps in the graph."
                    : "Draft a safe note proposal without mutating the vault."}
            </p>
            <button className="primary-button" disabled={busy || !composer.prompt.trim()} type="submit">
              {busy ? "Working..." : "Send"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

function MessageBubble({ chatId, message, onTaskPlanUpdate }) {
  const reasoningBadge = buildReasoningBadge(message);

  return (
    <article className={`message ${message.role}`}>
      <div className="message-header">
        <div className="message-title-row">
          <span className="message-role">{message.label}</span>
          {reasoningBadge ? (
            <span className={`reasoning-badge ${reasoningBadge.className}`}>
              {reasoningBadge.label}
            </span>
          ) : null}
        </div>
        {message.meta ? <span className="message-meta">{message.meta}</span> : null}
      </div>
      {message.payload ? (
        <StructuredResult
          chatId={chatId}
          messageId={message.id}
          payload={message.payload}
          kind={message.kind}
          onTaskPlanUpdate={onTaskPlanUpdate}
        />
      ) : (
        <pre>{message.text}</pre>
      )}
    </article>
  );
}

function StructuredResult({ chatId, messageId, payload, kind, onTaskPlanUpdate }) {
  if (kind === "analyze") {
    return (
      <div className="structured-stack">
        <pre>{payload.summary}</pre>
        {payload.notes?.length ? <InfoList title="Notes" items={payload.notes} /> : null}
        {payload.suggestions?.length ? (
          <InfoList title="Suggestions" items={payload.suggestions} />
        ) : null}
      </div>
    );
  }

  if (kind === "draft") {
    return (
      <div className="structured-stack">
        <pre>{payload.summary}</pre>
        <pre>{payload.content}</pre>
        {payload.citations?.length ? <InfoList title="Citations" items={payload.citations} /> : null}
      </div>
    );
  }

  if (kind === "agent") {
    return (
      <div className="structured-stack">
        <KeyValueGrid items={payload.summaryItems} />
        {payload.taskPlan ? (
          <section className="agent-section">
            <h3>Task Plan</h3>
            <pre>{payload.taskPlan.summary}</pre>
            <TaskPlanList
              chatId={chatId}
              messageId={messageId}
              items={payload.taskPlan.entries ?? []}
              onTaskPlanUpdate={onTaskPlanUpdate}
            />
            {payload.taskPlan.validationChecks?.length ? (
              <InfoList title="Validation Checks" items={payload.taskPlan.validationChecks} />
            ) : null}
          </section>
        ) : null}
        <section className="agent-section">
          <h3>Plan Output</h3>
          <pre>{payload.answer}</pre>
        </section>
        {payload.discussionTrace ? (
          <DetailCardList
            title="Discussion Trace"
            items={[
              {
                label: `Preset | ${discussionPresetLabels[payload.discussionTrace.preset] ?? payload.discussionTrace.preset ?? "custom"}`,
                body: payload.discussionTrace.plannerDraft || "none",
              },
              { label: "Critic Feedback", body: payload.discussionTrace.criticFeedback || "none" },
              { label: "Synthesis Output", body: payload.discussionTrace.synthesisOutput || "none" },
              { label: "Fallback Used", body: payload.discussionTrace.fallbackUsed || "none" },
            ]}
            renderMeta={(item) => item.label}
            renderBody={(item) => item.body}
          />
        ) : null}
        {payload.steps?.length ? (
          <DetailCardList
            title="Timeline"
            items={payload.steps}
            renderMeta={(item) => `${item.kind} | ${item.title}`}
            renderBody={(item) => item.observation}
          />
        ) : null}
        {payload.actions?.length ? (
          <DetailCardList
            title="Recommended Actions"
            items={payload.actions}
            renderMeta={(item) => `${item.action_type} | ${item.title}`}
            renderBody={(item) => `${item.target}\n${item.instruction}`}
          />
        ) : null}
        {payload.executions?.length ? (
          <DetailCardList
            title="Executed Actions"
            items={payload.executions}
            renderMeta={(item) => `${item.action_type} | ${item.status}`}
            renderBody={(item) => `${item.target}\n${item.output_text}`}
          />
        ) : null}
        {payload.citations?.length ? <InfoList title="Citations" items={payload.citations} /> : null}
      </div>
    );
  }

  return (
    <div className="structured-stack">
      <pre>{payload.answer}</pre>
      {payload.citations?.length ? <InfoList title="Citations" items={payload.citations} /> : null}
      {payload.context?.length ? <InfoList title="Context" items={payload.context} /> : null}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <p className="sidebar-kicker">Minimal Chat UI</p>
      <h3>Start with one focused request.</h3>
      <p>
        Ask a coding question, analyze a directory, draft a note, or scope a larger implementation
        task. Each chat stays separate, and you can switch between them from the sidebar.
      </p>
    </div>
  );
}

function InfoList({ title, items }) {
  return (
    <section className="info-list-section">
      <h3>{title}</h3>
      <ul className="info-list">
        {items.map((item, index) => (
          <li key={`${title}-${index}`}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function KeyValueGrid({ items }) {
  return (
    <section className="kv-grid">
      {items.map((item) => (
        <div className="kv-card" key={item.label}>
          <p className="kv-label">{item.label}</p>
          <p className="kv-value">{item.value}</p>
        </div>
      ))}
    </section>
  );
}

function DetailCardList({ title, items, renderMeta, renderBody }) {
  return (
    <section className="agent-section">
      <h3>{title}</h3>
      <div className="detail-card-list">
        {items.map((item, index) => (
          <article className="detail-card" key={`${title}-${index}`}>
            <p className="detail-card-index">{index + 1}</p>
            <div className="detail-card-copy">
              <p className="detail-card-meta">{renderMeta(item)}</p>
              <pre>{renderBody(item)}</pre>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function TaskPlanList({ chatId, messageId, items, onTaskPlanUpdate }) {
  return (
    <section className="agent-section">
      <h3>Planned Tasks</h3>
      <div className="detail-card-list">
        {items.map((item, index) => (
          <article className={`detail-card task-plan-card status-${item.status}`} key={`plan-${index}`}>
            <p className="detail-card-index">{item.step_index}</p>
            <div className="detail-card-copy">
              <p className="detail-card-meta">{`${item.status} | ${item.source_section}`}</p>
              <pre>{`${item.title}\n${item.details}`}</pre>
              <div className="task-plan-actions">
                {item.status !== "completed" ? (
                  <button
                    className="ghost-button compact"
                    onClick={() => onTaskPlanUpdate(chatId, messageId, index, "complete")}
                    type="button"
                  >
                    Mark Done
                  </button>
                ) : null}
                {item.status !== "next" ? (
                  <button
                    className="ghost-button compact"
                    onClick={() => onTaskPlanUpdate(chatId, messageId, index, "make-current")}
                    type="button"
                  >
                    Make Current
                  </button>
                ) : null}
                {item.status !== "pending" ? (
                  <button
                    className="ghost-button compact"
                    onClick={() => onTaskPlanUpdate(chatId, messageId, index, "reset")}
                    type="button"
                  >
                    Reset
                  </button>
                ) : null}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function Field({ label, value, onChange, options = null, labels = {}, placeholder = "" }) {
  return (
    <label className="field">
      <span>{label}</span>
      {options ? (
        <select value={value} onChange={(event) => onChange(event.target.value)}>
          {options.map((option) => (
            <option key={option} value={option}>
              {labels[option] ?? option}
            </option>
          ))}
        </select>
      ) : (
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
        />
      )}
    </label>
  );
}

function StatusBanner({ type, message }) {
  return <div className={`status-banner ${type}`}>{message}</div>;
}

function buildUserMessage(composer, workflowLabel) {
  return {
    id: crypto.randomUUID(),
    role: "user",
    kind: composer.workflow,
    label: workflowLabel,
    text: composer.prompt,
    meta: buildUserMeta(composer),
  };
}

function buildAssistantMessage({ workflow, model, reasoningMode, result, route = null }) {
  const discussionPreset = result?.discussion_preset;
  const metaParts = [];
  if (model) {
    metaParts.push(`model ${model}`);
  }
  if (route) {
    metaParts.push(`auto->${route.workflow}`);
  }
  metaParts.push(`reasoning ${reasoningMode}`);
  if (discussionPreset) {
    metaParts.push(`preset ${discussionPreset}`);
  }
  if (route?.confidence) {
    metaParts.push(String(route.confidence));
  }
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    kind: workflow,
    label: "Assistant",
    reasoningMode,
    routeWorkflow: route?.workflow ?? null,
    meta: metaParts.join(" | "),
    payload: normalizeResult(workflow, result),
  };
}

function buildSystemMessage(text) {
  return {
    id: crypto.randomUUID(),
    role: "system",
    kind: "system",
    label: "System",
    text,
    meta: formatTimestamp(new Date().toISOString()),
  };
}

function buildReasoningBadge(message) {
  if (!message || message.role !== "assistant" || !message.reasoningMode) {
    return null;
  }

  if (message.routeWorkflow && message.reasoningMode === "high") {
    return { label: "Auto High", className: "auto-high" };
  }
  if (message.reasoningMode === "high") {
    return { label: "High", className: "high" };
  }
  return { label: "Standard", className: "standard" };
}

function normalizeResult(workflow, result) {
  if (workflow === "analyze") {
    return {
      summary: `directory: ${result.directory}\nnote_count: ${result.note_count}\ntotal_links: ${result.total_links}\ninternal_link_count: ${result.internal_link_count}\ncross_directory_link_count: ${result.cross_directory_link_count}`,
      notes: (result.notes ?? []).map((note) => `${note.path} | ${note.title}`),
      suggestions: (result.suggestions ?? []).map(
        (item) => `${item.title} [${item.source}] | ${item.reason}`,
      ),
    };
  }

  if (workflow === "draft") {
    return {
      summary: `action: ${result.proposal?.action ?? ""}\ntarget_path: ${result.proposal?.target_path ?? ""}\ntitle: ${result.proposal?.title ?? ""}`,
      content: result.content ?? "",
      citations: result.citations ?? [],
    };
  }

  if (workflow === "agent") {
    const overview = result.overview ?? {};
    return {
      summaryItems: [
        { label: "Status", value: result.status ?? "" },
        { label: "Task Mode", value: result.task_mode ?? "" },
        { label: "Goal", value: result.normalized_goal ?? "" },
        { label: "Discussion", value: result.discussion_preset ?? "custom" },
        { label: "Steps", value: String(overview.step_count ?? 0) },
        { label: "Planned Tasks", value: String(overview.planned_task_count ?? 0) },
        { label: "Actions", value: String(overview.recommended_action_count ?? 0) },
        { label: "Executed", value: String(overview.executed_action_count ?? 0) },
      ],
      answer: result.final_output ?? "",
      taskPlan: result.task_plan
        ? {
            summary: result.task_plan.summary ?? "",
            goal: result.task_plan.goal ?? "",
            currentFocus: result.task_plan.current_focus ?? "",
            entries: result.task_plan.entries ?? [],
            validationChecks: result.task_plan.validation_checks ?? [],
          }
        : null,
      historyEntryId: result.history_entry_id ?? null,
      steps: result.steps ?? [],
      actions: result.recommended_actions ?? [],
      executions: result.action_executions ?? [],
      discussionTrace: result.discussion_trace
        ? {
            preset: result.discussion_trace.preset ?? "",
            plannerDraft: result.discussion_trace.planner_draft ?? "",
            criticFeedback: result.discussion_trace.critic_feedback ?? "",
            synthesisOutput: result.discussion_trace.synthesis_output ?? "",
            fallbackUsed: result.discussion_trace.fallback_used ?? "",
          }
        : null,
      citations: result.citations ?? [],
    };
  }

  return {
    answer: result.answer_text ?? "",
    citations: result.citations ?? [],
    context: [
      ...formatRetrievalItems(result.prompt?.retrieval?.primary_notes ?? []),
      ...formatRetrievalItems(result.prompt?.retrieval?.related_notes ?? []),
    ],
  };
}

function formatRetrievalItems(items) {
  return items.map(
    (item) =>
      `${item.note.path} | ${item.note.title} | score ${item.score} | ${item.reason}`,
  );
}

function buildUserMeta(composer) {
  if (composer.workflow === "analyze") {
    return `directory ${composer.directory}`;
  }
  if (composer.workflow === "draft") {
    return `${composer.model} | ${composer.targetDir}`;
  }
  return `${composer.model} | ${composer.reasoningMode} | ${composer.scopeText}`;
}

function resolveManualReasoningMode(reasoningMode) {
  if (reasoningMode === "high") {
    return "high";
  }
  if (reasoningMode === "standard") {
    return "standard";
  }
  return "high";
}

function buildConversationHistory(messages) {
  return messages
    .map(convertMessageToConversationTurn)
    .filter(Boolean)
    .slice(-8);
}

function convertMessageToConversationTurn(message) {
  if (!message || (message.role !== "user" && message.role !== "assistant")) {
    return null;
  }

  const content = extractMessageContent(message).trim();
  if (!content) {
    return null;
  }

  return {
    role: message.role,
    content,
  };
}

function extractMessageContent(message) {
  if (typeof message.text === "string" && message.text.trim()) {
    return message.text;
  }

  if (!message.payload) {
    return "";
  }

  if (message.kind === "agent") {
    return [message.payload.answer, ...(message.payload.summaryItems ?? []).map((item) => `${item.label}: ${item.value}`)]
      .filter(Boolean)
      .join("\n");
  }

  if (message.kind === "draft") {
    return [message.payload.summary, message.payload.content].filter(Boolean).join("\n\n");
  }

  if (message.kind === "analyze") {
    return [message.payload.summary, ...(message.payload.suggestions ?? [])].filter(Boolean).join("\n");
  }

  return message.payload.answer ?? "";
}

function createChatSession() {
  const timestamp = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "New Chat",
    createdAt: timestamp,
    updatedAt: timestamp,
    messages: [],
  };
}

function loadStoredChats() {
  try {
    const raw = window.localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function deriveChatTitle(currentTitle, text) {
  if (currentTitle && currentTitle !== "New Chat") {
    return currentTitle;
  }
  return truncateText(text.replace(/\s+/g, " ").trim(), 38) || "New Chat";
}

function truncateText(value, maxLength) {
  if (!value || value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 3).trimEnd()}...`;
}

function formatTimestamp(value) {
  const date = new Date(value);
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function placeholderForWorkflow(workflow) {
  if (workflow === "agent") {
    return "Build the mandatory part of minishell as a grounded agent task, but break it into executable first slices instead of pretending the whole project is done.";
  }
  if (workflow === "implementation") {
    return "Break the task into implementation slices for a 42 minishell that should actually compile.";
  }
  if (workflow === "analyze") {
    return "Analyze this knowledge slice and tell me what is missing from the graph.";
  }
  if (workflow === "draft") {
    return "Write a note about C parser cleanup rules and safe resource ownership.";
  }
  return "Implement a parser for minishell redirections in C and ground the answer in my notes.";
}

function updateTaskPlanState(taskPlan, entryIndex, action) {
  const entries = (taskPlan.entries ?? []).map((entry) => ({ ...entry }));
  if (!entries[entryIndex]) {
    return taskPlan;
  }

  if (action === "complete") {
    entries[entryIndex].status = "completed";
  } else if (action === "make-current") {
    for (const entry of entries) {
      if (entry.status === "next") {
        entry.status = "pending";
      }
    }
    if (entries[entryIndex].status !== "completed") {
      entries[entryIndex].status = "next";
    }
  } else if (action === "reset") {
    entries[entryIndex].status = "pending";
  }

  let hasNext = entries.some((entry) => entry.status === "next");
  if (!hasNext) {
    const firstPending = entries.find((entry) => entry.status !== "completed");
    if (firstPending) {
      firstPending.status = "next";
      hasNext = true;
    }
  }

  if (hasNext) {
    let seenNext = false;
    for (const entry of entries) {
      if (entry.status === "next" && !seenNext) {
        seenNext = true;
        continue;
      }
      if (entry.status === "next") {
        entry.status = "pending";
      }
    }
  }

  const completedCount = entries.filter((entry) => entry.status === "completed").length;
  const currentEntry = entries.find((entry) => entry.status === "next");
  const summary = `${entries.length} planned implementation tasks. ${completedCount} completed, ${Math.max(entries.length - completedCount, 0)} remaining.`;

  return {
    ...taskPlan,
    currentFocus: currentEntry?.title ?? taskPlan.currentFocus,
    summary,
    entries,
  };
}

function serializeTaskPlanForApi(taskPlan) {
  return {
    goal: taskPlan.goal ?? "",
    current_focus: taskPlan.currentFocus ?? "",
    summary: taskPlan.summary ?? "",
    entries: (taskPlan.entries ?? []).map((entry) => ({
      step_index: entry.step_index,
      title: entry.title,
      status: entry.status,
      details: entry.details,
      source_section: entry.source_section,
    })),
    validation_checks: taskPlan.validationChecks ?? [],
  };
}

export default App;
