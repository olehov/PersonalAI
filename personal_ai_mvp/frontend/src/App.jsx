import { useEffect, useMemo, useState } from "react";

import {
  analyzeDirectory,
  askQuestion,
  autoRoute,
  draftNote,
  getHealthStatus,
  getHistoryOverview,
  listAgentHistory,
  listAskHistory,
  listBenchmarkHistory,
  listModels,
  reloadVault,
  runAgentRuntime,
  scopeImplementation,
  updateAgentTaskPlan,
} from "./api.js";

const STANDARD_MODEL_VALUE = "__standard__";
const DEFAULT_MODEL = STANDARD_MODEL_VALUE;
const CHAT_STORAGE_KEY = "personal-ai-chat-sessions";
const HISTORY_LIMIT = 12;

const discussionPresetOptions = [
  { value: "heavy_synthesis", label: "Heavy Synthesis" },
  { value: "coder_critic", label: "Coder Critic" },
  { value: "fast", label: "Fast Debate" },
];

const discussionPresetLabels = Object.fromEntries(
  discussionPresetOptions.map((option) => [option.value, option.label]),
);

const composerDefaults = {
  reasoningMode: "auto",
  discussionPreset: "heavy_synthesis",
  prompt: "",
  model: DEFAULT_MODEL,
  scopeText: "Projects, Languages/C",
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
  const [benchmarkHistoryEntries, setBenchmarkHistoryEntries] = useState([]);
  const [historyOverview, setHistoryOverview] = useState({
    ask: 0,
    agent: 0,
    benchmark: 0,
  });
  const [healthStatus, setHealthStatus] = useState(null);

  const activeChat = useMemo(
    () => chatSessions.find((chat) => chat.id === activeChatId) ?? null,
    [activeChatId, chatSessions],
  );
  const activeProgressMessage = useMemo(
    () => getLatestProgressMessage(activeChat?.messages ?? []),
    [activeChat],
  );
  const activeProgressStage = useMemo(
    () => getCurrentProgressStage(activeProgressMessage?.payload?.stages ?? []),
    [activeProgressMessage],
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
    await Promise.all([
      loadModels(),
      refreshHealthStatus(),
      refreshHistory(),
      refreshAgentHistory(),
      refreshBenchmarkHistory(),
      refreshHistoryOverview(),
    ]);
  }

  async function loadModels() {
    try {
      const payload = await listModels();
      const listedModels = payload.models?.length ? payload.models : [payload.default_model ?? "gemma:latest"];
      const models = [STANDARD_MODEL_VALUE, ...listedModels.filter((item) => item !== STANDARD_MODEL_VALUE)];
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

  async function refreshBenchmarkHistory() {
    try {
      const payload = await listBenchmarkHistory(HISTORY_LIMIT);
      setBenchmarkHistoryEntries(payload.entries ?? []);
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

  async function refreshHealthStatus() {
    try {
      const payload = await getHealthStatus();
      setHealthStatus(payload);
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

  function handleStarterPrompt(prompt) {
    setComposer((current) => ({
      ...current,
      prompt,
    }));
  }

  function handleDeleteChat(chatId) {
    setChatSessions((current) => {
      const nextChats = current.filter((chat) => chat.id !== chatId);
      if (nextChats.length > 0) {
        if (chatId === activeChatId) {
          setActiveChatId(nextChats[0].id);
        }
        return nextChats;
      }
      const fallbackChat = createChatSession();
      setActiveChatId(fallbackChat.id);
      return [fallbackChat];
    });
  }

  async function handleReloadVault() {
    setBusy(true);
    try {
      await reloadVault();
      await Promise.all([
        refreshHealthStatus(),
        refreshHistory(),
        refreshAgentHistory(),
        refreshBenchmarkHistory(),
        refreshHistoryOverview(),
      ]);
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

    const chatId = activeChat.id;
    const userMessage = buildUserMessage(composer);
    const progressMessage = buildProgressMessage();
    const chatHistory = buildConversationHistory(activeChat.messages);

    appendMessages(chatId, [userMessage, progressMessage]);
    setBusy(true);

    try {
      const execution = await runWorkflow({
        composer,
        chatHistory,
        onProgress: (payload) => {
          replaceMessage(chatId, progressMessage.id, (message) => ({
            ...message,
            meta: payload.meta ?? message.meta,
            payload,
          }));
        },
      });

      removeMessage(chatId, progressMessage.id);

      appendMessage(
        chatId,
        buildAssistantMessage({
          workflow: execution.workflow,
          model: execution.result?.model ?? composer.model,
          reasoningMode: execution.reasoningMode,
          result: execution.result,
          route: execution.route ?? null,
          execution: execution.execution ?? execution.result?.execution ?? null,
        }),
      );

      setChatSessions((current) =>
        current.map((chat) =>
          chat.id === chatId
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
      }));
      await Promise.all([
        refreshHistory(),
        refreshAgentHistory(),
        refreshBenchmarkHistory(),
        refreshHistoryOverview(),
      ]);
      setStatus({
        type: "info",
        message: `${execution.route?.workflow ?? execution.workflow ?? "request"} completed.`,
      });
    } catch (error) {
      replaceMessage(chatId, progressMessage.id, (message) => ({
        ...message,
        kind: "system",
        label: "System",
        text: `Request failed: ${error.message}`,
        payload: null,
        meta: formatTimestamp(new Date().toISOString()),
      }));
      setStatus({
        type: "error",
        message: error.message,
      });
    } finally {
      setBusy(false);
    }
  }

  async function runWorkflow({ composer: currentComposer, chatHistory, onProgress }) {
    const selectedModel = resolveApiModel(currentComposer.model);
    const routePayload = await autoRoute({
      prompt: currentComposer.prompt,
      chatHistory,
      title: "",
      directory: "",
      targetDir: "Inbox",
    });

    const route = routePayload.route ?? { workflow: "ask", reasoning_mode: "standard" };
    const preprocess = routePayload.preprocess ?? null;
    const reasoningMode = currentComposer.reasoningMode === "auto"
      ? route.reasoning_mode ?? "standard"
      : currentComposer.reasoningMode;

    const stageTemplate = buildProgressStages(route.workflow);
    onProgress({
      status: "running",
      summary: progressSummaryForWorkflow(route.workflow),
      meta: `routing complete | ${route.workflow}`,
      stages: markStagesActive(stageTemplate, 1),
      preprocess,
    });

    const executionPayload = await executeWorkflow({
      workflow: route.workflow,
      composer: currentComposer,
      selectedModel,
      chatHistory,
      reasoningMode,
      route,
      onProgress,
      stageTemplate,
      preprocess,
    });

    return {
      workflow: route.workflow,
      reasoningMode,
      result: executionPayload.result,
      route,
      execution: executionPayload.execution ?? executionPayload.result?.execution ?? null,
    };
  }

  async function executeWorkflow({
    workflow,
    composer: currentComposer,
    selectedModel,
    chatHistory,
    reasoningMode,
    route,
    onProgress,
    stageTemplate,
    preprocess,
  }) {
    let stageIndex = 1;
    const advanceProgress = () => {
      stageIndex = Math.min(stageIndex + 1, stageTemplate.length - 1);
      onProgress({
        status: "running",
        summary: progressSummaryForWorkflow(workflow),
        meta: `${workflow} | ${stageTemplate[stageIndex].title}`,
        stages: markStagesActive(stageTemplate, stageIndex),
        preprocess,
      });
    };

    const ticker = window.setInterval(advanceProgress, 1100);

    try {
      if (workflow === "agent") {
        const response = await runAgentRuntime({
          requestText: currentComposer.prompt,
          model: selectedModel,
          scopeText: currentComposer.scopeText,
          chatHistory,
          reasoningMode,
          discussionPreset: currentComposer.discussionPreset,
        });
        return finalizeWorkflowResponse({
          response,
          workflow,
          onProgress,
          stageTemplate,
          preprocess,
        });
      }

      if (workflow === "implementation") {
        const response = await scopeImplementation({
          requestText: currentComposer.prompt,
          model: selectedModel,
          scopeText: currentComposer.scopeText,
          chatHistory,
          reasoningMode,
        });
        return finalizeWorkflowResponse({
          response,
          workflow,
          onProgress,
          stageTemplate,
          preprocess,
        });
      }

      if (workflow === "draft") {
        const response = await draftNote({
          title: route.derived_title || deriveDraftTitle(currentComposer.prompt),
          instruction: currentComposer.prompt,
          model: selectedModel,
          targetDir: "Inbox",
          scopeText: currentComposer.scopeText,
        });
        return finalizeWorkflowResponse({
          response,
          workflow,
          onProgress,
          stageTemplate,
          preprocess,
        });
      }

      if (workflow === "analyze") {
        const response = await analyzeDirectory({
          directory: route.derived_directory || currentComposer.scopeText.split(",")[0]?.trim() || "Projects",
        });
        return finalizeWorkflowResponse({
          response,
          workflow,
          onProgress,
          stageTemplate,
          preprocess,
        });
      }

      const response = await askQuestion({
        question: currentComposer.prompt,
        model: selectedModel,
        scopeText: currentComposer.scopeText,
        chatHistory,
        reasoningMode,
      });
      return finalizeWorkflowResponse({
        response,
        workflow,
        onProgress,
        stageTemplate,
        preprocess,
      });
    } finally {
      window.clearInterval(ticker);
    }
  }

  function appendMessage(chatId, message) {
    appendMessages(chatId, [message]);
  }

  function appendMessages(chatId, messages) {
    setChatSessions((current) =>
      current.map((chat) =>
        chat.id === chatId
          ? {
              ...chat,
              updatedAt: new Date().toISOString(),
              messages: [...chat.messages, ...messages],
            }
          : chat,
      ),
    );
  }

  function replaceMessage(chatId, messageId, updater) {
    setChatSessions((current) =>
      current.map((chat) =>
        chat.id === chatId
          ? {
              ...chat,
              updatedAt: new Date().toISOString(),
              messages: chat.messages.map((message) =>
                message.id === messageId ? updater(message) : message,
              ),
            }
          : chat,
      ),
    );
  }

  function removeMessage(chatId, messageId) {
    setChatSessions((current) =>
      current.map((chat) =>
        chat.id === chatId
          ? {
              ...chat,
              updatedAt: new Date().toISOString(),
              messages: chat.messages.filter((message) => message.id !== messageId),
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

  function importBenchmarkHistoryEntry(entry) {
    const result = entry.result_payload ?? {};
    const importedChat = {
      id: crypto.randomUUID(),
      title: truncateText(entry.task_id, 42) || "Imported benchmark run",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [
        {
          id: crypto.randomUUID(),
          role: "user",
          kind: "benchmark-history-import",
          label: "Imported Benchmark Task",
          text: entry.prompt_text,
          meta: `${entry.model} | ${entry.workflow} | ${entry.created_at}`,
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          kind: "benchmark",
          label: "Imported Benchmark Run",
          meta: `status ${entry.status} | latency ${entry.latency_ms ?? "n/a"} ms`,
          payload: normalizeResult("benchmark", {
            ...result,
            task_id: entry.task_id,
            pack_id: entry.pack_id,
            category: entry.category,
            workflow: entry.workflow,
            model: entry.model,
            status: entry.status,
            prompt_text: entry.prompt_text,
            latency_ms: entry.latency_ms,
          }),
        },
      ],
    };

    setChatSessions((current) => [importedChat, ...current]);
    setActiveChatId(importedChat.id);
    setStatus({
      type: "info",
      message: "Benchmark history entry imported as a chat.",
    });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div>
            <p className="sidebar-kicker">PersonalAI</p>
            <h1>Chats</h1>
            {healthStatus?.web_search ? (
              <p className="sidebar-meta">
                Web search: {formatWebSearchHealthLabel(healthStatus.web_search)}
              </p>
            ) : null}
          </div>
          <button className="primary-button sidebar-new-chat" onClick={handleNewChat} type="button">
            New chat
          </button>
        </div>

        <div className="sidebar-group">
          <p className="sidebar-group-label">Recent Chats</p>
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
                  {formatTimestamp(chat.updatedAt)} - {chat.messages.length} msgs
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
                  x
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-group sidebar-history">
          <div className="sidebar-section-header">
            <p className="sidebar-group-label">Saved Runs</p>
            <button
              className="text-button"
              onClick={() => Promise.all([refreshHistory(), refreshAgentHistory(), refreshBenchmarkHistory()])}
              type="button"
            >
              Refresh
            </button>
          </div>

          <HistoryGroup
            title={`Ask / Scope (${historyOverview.ask})`}
            entries={historyEntries}
            emptyLabel="No saved ask runs yet."
            renderTitle={(entry) => truncateText(entry.question, 54)}
            renderMeta={(entry) => `${entry.model} - ${entry.task_mode}`}
            onOpen={importHistoryEntry}
          />

          <HistoryGroup
            title={`Agent Runs (${historyOverview.agent})`}
            entries={agentHistoryEntries}
            emptyLabel="No saved agent runs yet."
            renderTitle={(entry) => truncateText(entry.normalized_goal || entry.request_text, 54)}
            renderMeta={(entry) => `${entry.model} - ${entry.artifact_payload?.discussion_preset ?? "custom"} - ${entry.status}`}
            onOpen={importAgentHistoryEntry}
          />

          <HistoryGroup
            title={`Benchmark Runs (${historyOverview.benchmark})`}
            entries={benchmarkHistoryEntries}
            emptyLabel="No saved benchmark runs yet."
            renderTitle={(entry) => truncateText(entry.task_id, 54)}
            renderMeta={(entry) => `${entry.model} - ${entry.workflow} - ${entry.status} - turns ${countBenchmarkTurns(entry.result_payload)}`}
            onOpen={importBenchmarkHistoryEntry}
          />
        </div>
      </aside>

      <main className="chat-layout">
        <header className="topbar">
          <div className="topbar-copy">
            <p className="sidebar-kicker">Local-first developer assistant</p>
            <h2>{activeChat?.title ?? "New Chat"}</h2>
            <p className="topbar-subtitle">
              Coding-first chat with grounded context, planner-aware execution, and saved runs.
            </p>
          </div>
          <div className="topbar-actions">
            {busy && activeProgressStage ? (
              <div className={`live-pill ${busy ? "running" : "idle"}`}>
                <span className="live-pill-dot" />
                <div className="live-pill-copy">
                  <strong>{busy ? "Working" : "Last run"}</strong>
                  <span>{activeProgressStage.title}</span>
                </div>
              </div>
            ) : null}
            <span className="model-pill">{formatSelectedModelLabel(composer.model)}</span>
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
            <EmptyState onStarterPick={handleStarterPrompt} />
          )}
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          {busy && activeProgressStage ? (
            <div className={`composer-runtime ${busy ? "running" : "idle"}`}>
              <span className="composer-runtime-label">Current stage</span>
              <strong>{activeProgressStage.title}</strong>
              <span>{activeProgressStage.detail}</span>
            </div>
          ) : null}
          <div className="composer-toolbar">
            <Field
              label="Reasoning"
              value={composer.reasoningMode}
              onChange={(value) => setComposer((current) => ({ ...current, reasoningMode: value }))}
              options={["auto", "standard", "high"]}
              labels={{ auto: "Auto", standard: "Standard", high: "High" }}
            />
            <Field
              label="Collab"
              value={composer.discussionPreset}
              onChange={(value) => setComposer((current) => ({ ...current, discussionPreset: value }))}
              options={discussionPresetOptions.map((option) => option.value)}
              labels={discussionPresetLabels}
            />
          </div>

          <div className="composer-scope-row">
            <input
              className="scope-input"
              value={composer.scopeText}
              onChange={(event) =>
                setComposer((current) => ({ ...current, scopeText: event.target.value }))
              }
              placeholder="Projects, Languages/C"
            />
          </div>

          <div className="composer-input-shell">
            <textarea
              value={composer.prompt}
              onChange={(event) =>
                setComposer((current) => ({ ...current, prompt: event.target.value }))
              }
              placeholder={composerPlaceholder()}
            />
            <button className="send-button" disabled={busy || !composer.prompt.trim()} type="submit">
              {busy ? "..." : "^"}
            </button>
          </div>

          <div className="composer-footer">
            <p className="muted-copy">
              Auto-routing picks the workflow first, then the UI shows the live execution stage while the backend works.
            </p>
          </div>
        </form>
      </main>
    </div>
  );
}

function HistoryGroup({ title, entries, emptyLabel, renderTitle, renderMeta, onOpen }) {
  return (
    <div className="history-group">
      <p className="history-group-title">{title}</p>
      {entries.length === 0 ? (
        <p className="muted-copy">{emptyLabel}</p>
      ) : (
        entries.map((entry) => (
          <div className="history-card" key={`${title}-${entry.entry_id}`}>
            <p className="history-card-title">{renderTitle(entry)}</p>
            <p className="history-card-meta">{renderMeta(entry)}</p>
            <button className="ghost-button compact" onClick={() => onOpen(entry)} type="button">
              Open
            </button>
          </div>
        ))
      )}
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
        <RichAnswerText text={message.text} />
      )}
    </article>
  );
}

function StructuredResult({ chatId, messageId, payload, kind, onTaskPlanUpdate }) {
  if (kind === "progress") {
    return (
      <div className="progress-panel">
        <div className="progress-panel-header">
          <p className="progress-summary">{payload.summary}</p>
          {payload.meta ? <span className="progress-panel-meta">{payload.meta}</span> : null}
        </div>
        <div className="progress-stage-list compact">
          {(payload.stages ?? []).map((stage, index) => (
            <article className={`progress-stage ${stage.status}`} key={`progress-${index}`}>
              <div className="progress-stage-icon">
                {stage.status === "completed" ? "done" : stage.status === "failed" ? "fail" : stage.status === "running" ? "now" : "next"}
              </div>
              <div className="progress-stage-copy">
                <p className="progress-stage-title">{stage.title}</p>
                <p className="progress-stage-detail">{stage.detail}</p>
              </div>
            </article>
          ))}
        </div>
        {payload.preprocess ? (
          <ProgressPreprocessCard preprocess={payload.preprocess} />
        ) : null}
      </div>
    );
  }

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
        {payload.runtimeFlow?.length ? (
          <RuntimeFlowSection items={payload.runtimeFlow} />
        ) : null}
        {payload.taskPlan ? (
          <section className="agent-section">
            <h3>Task Plan</h3>
            <pre>{payload.taskPlan.summary}</pre>
            <TaskPlanList
              chatId={chatId}
              messageId={messageId}
              items={payload.taskPlan.entries}
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
                label: `Preset - ${discussionPresetLabels[payload.discussionTrace.preset] ?? payload.discussionTrace.preset ?? "custom"}`,
                body: payload.discussionTrace.plannerDraft || "none",
              },
              { label: "Critic Feedback", body: payload.discussionTrace.criticFeedback || "none" },
              { label: "Synthesis Output", body: payload.discussionTrace.synthesisOutput || "none" },
              {
                label: `Approver - ${payload.discussionTrace.approvalStatus || "unknown"} - revisions ${payload.discussionTrace.plannerRevisions ?? 0} - rollbacks ${payload.discussionTrace.plannerRollbacks ?? 0}`,
                body: payload.discussionTrace.approverFeedback || "none",
              },
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
            renderMeta={(item) => `${item.kind} - ${item.title}`}
            renderBody={(item) => item.observation}
          />
        ) : null}
        {payload.actions?.length ? (
          <DetailCardList
            title="Recommended Actions"
            items={payload.actions}
            renderMeta={(item) => `${item.action_type} - ${item.title}`}
            renderBody={(item) => `${item.target}\n${item.instruction}`}
          />
        ) : null}
        {payload.executions?.length ? (
          <DetailCardList
            title="Executed Actions"
            items={payload.executions}
            renderMeta={(item) => `${item.action_type} - ${item.status}`}
            renderBody={(item) => `${item.target}\n${item.output_text}`}
          />
        ) : null}
        {payload.citations?.length ? <InfoList title="Citations" items={payload.citations} /> : null}
      </div>
    );
  }

  if (kind === "benchmark") {
    return (
      <div className="structured-stack">
        <KeyValueGrid items={payload.summaryItems} />
        {payload.turnResults?.length ? (
          <DetailCardList
            title="Turn Results"
            items={payload.turnResults}
            renderMeta={(item) => `turn ${item.turnIndex} - ${item.status}`}
            renderBody={(item) => `${item.prompt}\n\n${item.preview}`}
          />
        ) : null}
        {payload.finalPreview ? (
          <section className="agent-section">
            <h3>Final Preview</h3>
            <pre>{payload.finalPreview}</pre>
          </section>
        ) : null}
      </div>
    );
  }

  return (
    <div className="structured-stack">
      <RichAnswerText text={payload.answer} />
      {payload.citations?.length ? <InfoList title="Citations" items={payload.citations} /> : null}
      {payload.webGrounding ? <WebGroundingPanel grounding={payload.webGrounding} /> : null}
      {payload.retrieval ? <RetrievalPanel retrieval={payload.retrieval} /> : null}
    </div>
  );
}

function RichAnswerText({ text }) {
  const blocks = splitTextBlocks(text ?? "");
  return (
    <div className="rich-text">
      {blocks.map((block, index) => {
        if (block.kind === "code") {
          return (
            <pre className="rich-code" key={`block-${index}`}>
              {block.content}
            </pre>
          );
        }
        if (block.kind === "list") {
          return (
            <ul className="rich-list" key={`block-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`item-${itemIndex}`}>{item}</li>
              ))}
            </ul>
          );
        }
        return (
          <p className="rich-paragraph" key={`block-${index}`}>
            {block.content}
          </p>
        );
      })}
    </div>
  );
}

function EmptyState({ onStarterPick }) {
  const starterPrompts = [
    "Explain how to design a minimal command parser for minishell in C.",
    "Review my C notes and suggest the next missing node to add to the graph.",
    "Plan the next safe implementation slice for PersonalAI chat memory.",
  ];

  return (
    <div className="empty-state">
      <p className="sidebar-kicker">Coding-first workspace</p>
      <h3>Start a new request.</h3>
      <p>
        Ask a focused coding question, continue an implementation slice, or let the agent plan the next
        safe step. Progress appears turn by turn while the backend works.
      </p>
      <div className="starter-list">
        {starterPrompts.map((prompt) => (
          <button
            className="starter-chip"
            key={prompt}
            onClick={() => onStarterPick(prompt)}
            type="button"
          >
            {prompt}
          </button>
        ))}
      </div>
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

function RetrievalPanel({ retrieval }) {
  const primaryNotes = retrieval.primaryNotes ?? [];
  const relatedNotes = retrieval.relatedNotes ?? [];
  if (primaryNotes.length === 0 && relatedNotes.length === 0) {
    return null;
  }

  return (
    <section className="agent-section retrieval-panel">
      <div className="retrieval-panel-header">
        <h3>Retrieval Context</h3>
        <span className="progress-panel-meta">
          {primaryNotes.length} primary | {relatedNotes.length} related
        </span>
      </div>
      {primaryNotes.length ? (
        <RetrievalNoteList title="Primary Notes" items={primaryNotes} />
      ) : null}
      {relatedNotes.length ? (
        <RetrievalNoteList title="Related Notes" items={relatedNotes} />
      ) : null}
    </section>
  );
}

function WebGroundingPanel({ grounding }) {
  if (!grounding || typeof grounding !== "object") {
    return null;
  }

  const policyEntries = buildWebGroundingPolicyEntries(grounding.policy);
  const results = Array.isArray(grounding.results) ? grounding.results : [];

  return (
    <section className="agent-section retrieval-panel">
      <div className="retrieval-panel-header">
        <h3>Web Grounding</h3>
        <span className="progress-panel-meta">{grounding.provider ?? "unknown"}</span>
      </div>
      <div className="debug-signal-grid">
        <article className="debug-signal-card">
          <p className="progress-preprocess-label">Original Query</p>
          <pre>{grounding.originalQuery || grounding.query || "n/a"}</pre>
        </article>
        <article className="debug-signal-card">
          <p className="progress-preprocess-label">Search Query</p>
          <pre>{grounding.query || "n/a"}</pre>
        </article>
        <article className="debug-signal-card">
          <p className="progress-preprocess-label">Query Status</p>
          <pre>{buildWebGroundingStatus(grounding)}</pre>
        </article>
      </div>
      {grounding.error ? (
        <div className="debug-signal-grid">
          <article className="debug-signal-card">
            <p className="progress-preprocess-label">Provider Error</p>
            <pre>{grounding.error}</pre>
          </article>
        </div>
      ) : null}
      {policyEntries.length ? (
        <div className="debug-signal-grid">
          {policyEntries.map((entry) => (
            <article className="debug-signal-card" key={entry.label}>
              <p className="progress-preprocess-label">{entry.label}</p>
              <pre>{entry.value}</pre>
            </article>
          ))}
        </div>
      ) : null}
      {results.length ? (
        <DetailCardList
          title="Web Results"
          items={results}
          renderMeta={(item) => `${item.source || "unknown"} - ${item.title || "untitled"}`}
          renderBody={(item) => `${item.url || ""}\n${item.snippet || ""}`.trim()}
        />
      ) : null}
    </section>
  );
}

function RetrievalNoteList({ title, items }) {
  return (
    <section className="retrieval-note-section">
      <h4>{title}</h4>
      <div className="retrieval-note-list">
        {items.map((item, index) => (
          <article className="retrieval-note-card" key={`${title}-${item.note.path}-${index}`}>
            <div className="retrieval-note-header">
              <div>
                <p className="retrieval-note-title">{item.note.title}</p>
                <p className="retrieval-note-path">{item.note.path}</p>
              </div>
              <span className="retrieval-note-score">score {item.score}</span>
            </div>
            <p className="retrieval-note-reason">{item.reason}</p>
            {item.debugSignals ? (
              <details className="retrieval-debug">
                <summary>Why this note</summary>
                <DebugSignalGrid debugSignals={item.debugSignals} />
              </details>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function DebugSignalGrid({ debugSignals }) {
  const entries = buildDebugSignalEntries(debugSignals);
  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="debug-signal-grid">
      {entries.map((entry) => (
        <article className="debug-signal-card" key={entry.label}>
          <p className="progress-preprocess-label">{entry.label}</p>
          <pre>{entry.value}</pre>
        </article>
      ))}
    </div>
  );
}

function ProgressPreprocessCard({ preprocess }) {
  const rows = buildPreprocessRows(preprocess);
  if (rows.length === 0) {
    return null;
  }

  return (
    <section className="progress-preprocess-card">
      <div className="progress-preprocess-header">
        <p className="sidebar-group-label">Generated Prompt</p>
        <span className="progress-panel-meta">{preprocess.mode ?? "disabled"}</span>
      </div>
      <div className="progress-preprocess-grid">
        {rows.map((row) => (
          <article className="progress-preprocess-row" key={row.label}>
            <p className="progress-preprocess-label">{row.label}</p>
            <pre>{row.value}</pre>
          </article>
        ))}
      </div>
    </section>
  );
}

function splitTextBlocks(text) {
  const normalized = String(text ?? "").replace(/\r\n/g, "\n").trim();
  if (!normalized) {
    return [];
  }

  const blocks = [];
  const codeFencePattern = /```[^\n]*\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeFencePattern.exec(normalized)) !== null) {
    const before = normalized.slice(lastIndex, match.index).trim();
    if (before) {
      blocks.push(...splitPlainBlocks(before));
    }
    blocks.push({
      kind: "code",
      content: match[1].trim(),
    });
    lastIndex = match.index + match[0].length;
  }

  const tail = normalized.slice(lastIndex).trim();
  if (tail) {
    blocks.push(...splitPlainBlocks(tail));
  }
  return blocks;
}

function splitPlainBlocks(text) {
  const chunks = text
    .split(/\n\s*\n/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);

  return chunks.map((chunk) => {
    const lines = chunk.split("\n").map((line) => line.trim()).filter(Boolean);
    const isList = lines.length > 1 && lines.every((line) => /^([-*]|\d+\.)\s+/.test(line));
    if (isList) {
      return {
        kind: "list",
        items: lines.map((line) => line.replace(/^([-*]|\d+\.)\s+/, "").trim()),
      };
    }
    return {
      kind: "paragraph",
      content: lines.join(" "),
    };
  });
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

function RuntimeFlowSection({ items }) {
  return (
    <section className="agent-section">
      <h3>Runtime Flow</h3>
      <div className="runtime-flow">
        {items.map((item, index) => (
          <article
            className={`runtime-step status-${item.status ?? "completed"} emphasis-${item.emphasis ?? "neutral"}`}
            key={`runtime-step-${index}`}
          >
            <p className="runtime-step-index">{index + 1}</p>
            <div className="runtime-step-copy">
              <p className="runtime-step-title">{item.title}</p>
              <p className="runtime-step-meta">{item.meta}</p>
              {item.detail ? <pre>{item.detail}</pre> : null}
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
              <p className="detail-card-meta">{`${item.status} - ${item.source_section}`}</p>
              <pre>{`${item.title}\n${item.details}`}</pre>
              <div className="task-plan-actions">
                {item.status !== "completed" ? (
                  <button
                    className="ghost-button compact"
                    onClick={() => onTaskPlanUpdate(chatId, messageId, index, "complete")}
                    type="button"
                  >
                    Mark done
                  </button>
                ) : null}
                {item.status !== "next" ? (
                  <button
                    className="ghost-button compact"
                    onClick={() => onTaskPlanUpdate(chatId, messageId, index, "make-current")}
                    type="button"
                  >
                    Make current
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

function buildUserMessage(composer) {
  return {
    id: crypto.randomUUID(),
    role: "user",
    kind: "codex",
    label: "Request",
    text: composer.prompt,
    meta: buildUserMeta(composer),
  };
}

function buildAssistantMessage({ workflow, model, reasoningMode, result, route = null, execution = null }) {
  const discussionPreset = result?.discussion_preset;
  const metaParts = [];
  const resolvedModel = execution?.resolved_model ?? model;
  const executedWorkflow = execution?.executed_workflow ?? workflow;
  if (resolvedModel) {
    metaParts.push(`model ${formatSelectedModelLabel(resolvedModel)}`);
  }
  if (route) {
    metaParts.push(`auto->${route.workflow}`);
  }
  if (executedWorkflow) {
    metaParts.push(`run ${executedWorkflow}`);
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
    execution,
    meta: metaParts.join(" - "),
    payload: normalizeResult(workflow, result),
  };
}

function buildProgressMessage() {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    kind: "progress",
    label: "Working",
    meta: "routing...",
    payload: {
      status: "running",
      summary: "Preparing the request flow.",
      stages: markStagesActive(buildProgressStages("ask"), 0),
    },
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

function buildRuntimeFlow(result) {
  if (!result || !result.discussion_trace) {
    return [];
  }

  const discussionTrace = result.discussion_trace;
  const flow = [
    {
      title: "Planner Draft",
      meta: result.model ?? "planner",
      detail: truncateText(discussionTrace.planner_draft ?? "", 220),
      status: "completed",
      emphasis: "planner",
    },
  ];

  if (discussionTrace.critic_feedback) {
    flow.push({
      title: "Discussion Critique",
      meta: result.critic_model ?? "critic",
      detail: truncateText(discussionTrace.critic_feedback, 220),
      status: "completed",
      emphasis: "discussion",
    });
  }

  if (discussionTrace.synthesis_output) {
    flow.push({
      title: "Planner Revision",
      meta: result.synthesis_model ?? result.model ?? "planner",
      detail: truncateText(discussionTrace.synthesis_output, 220),
      status: "completed",
      emphasis: "planner",
    });
  }

  if (discussionTrace.approval_status || discussionTrace.approver_feedback) {
    flow.push({
      title: "Approver Review",
      meta: `${result.approver_model ?? result.synthesis_model ?? result.model ?? "approver"} - ${discussionTrace.approval_status ?? "unknown"}`,
      detail: truncateText(discussionTrace.approver_feedback ?? "", 220),
      status: discussionTrace.approval_status === "approved" ? "completed" : "rollback",
      emphasis: "approver",
    });
  }

  if ((discussionTrace.planner_rollbacks ?? 0) > 0) {
    flow.push({
      title: "Rollback To Planner",
      meta: `${discussionTrace.planner_rollbacks} rollback(s)`,
      detail: `Planner revisions: ${discussionTrace.plannerRevisions ?? discussionTrace.planner_revisions ?? 0}`,
      status: "rollback",
      emphasis: "rollback",
    });
  }

  if ((result.action_executions ?? []).length > 0) {
    const executedCount = (result.action_executions ?? []).filter((item) => item.status === "executed").length;
    flow.push({
      title: "Executor Pass",
      meta: `${result.executor_model ?? result.model ?? "executor"} - executed ${executedCount}/${(result.action_executions ?? []).length}`,
      detail: truncateText(result.final_output ?? "", 220),
      status: "completed",
      emphasis: "executor",
    });
  }

  return flow;
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
            approverFeedback: result.discussion_trace.approver_feedback ?? "",
            approvalStatus: result.discussion_trace.approval_status ?? "",
            plannerRevisions: result.discussion_trace.planner_revisions ?? 0,
            plannerRollbacks: result.discussion_trace.planner_rollbacks ?? 0,
            fallbackUsed: result.discussion_trace.fallback_used ?? "",
          }
        : null,
      citations: result.citations ?? [],
      runtimeFlow: buildRuntimeFlow(result),
    };
  }

  if (workflow === "benchmark") {
    const turnResults = Array.isArray(result.turn_results)
      ? result.turn_results.map((turn) => ({
          turnIndex: turn.turn_index ?? "?",
          status: turn.status ?? "unknown",
          prompt: turn.prompt ?? "",
          preview: buildBenchmarkPreview(turn.result_payload ?? {}),
        }))
      : [];
    return {
      summaryItems: [
        { label: "Pack", value: result.pack_id ?? "" },
        { label: "Task", value: result.task_id ?? "" },
        { label: "Category", value: result.category ?? "" },
        { label: "Workflow", value: result.workflow ?? "" },
        { label: "Model", value: result.model ?? "" },
        { label: "Status", value: result.status ?? result.final_status ?? "" },
        { label: "Latency", value: result.latency_ms != null ? `${result.latency_ms} ms` : "n/a" },
        { label: "Turns", value: String(turnResults.length) },
      ],
      turnResults,
      finalPreview: buildBenchmarkPreview(result.final_payload ?? result),
    };
  }

  return {
    answer: result.answer_text ?? "",
    citations: result.citations ?? [],
    retrieval: formatRetrievalBundle(result.prompt?.retrieval),
    webGrounding: formatWebGroundingBundle(result.web_grounding),
  };
}

function formatRetrievalBundle(retrieval) {
  if (!retrieval || typeof retrieval !== "object") {
    return null;
  }
  return {
    primaryNotes: formatRetrievalItems(retrieval.primary_notes ?? []),
    relatedNotes: formatRetrievalItems(retrieval.related_notes ?? []),
  };
}

function formatRetrievalItems(items) {
  return items.map((item) => ({
    note: {
      path: item.note?.path ?? "",
      title: item.note?.title ?? "",
    },
    score: item.score ?? 0,
    reason: item.reason ?? "",
    debugSignals: item.debug_signals ?? null,
  }));
}

function formatWebGroundingBundle(grounding) {
  if (!grounding || typeof grounding !== "object") {
    return null;
  }

  return {
    provider: grounding.provider ?? "",
    query: grounding.query ?? "",
    originalQuery: grounding.original_query ?? "",
    queryTruncated: grounding.query_truncated === true,
    degraded: grounding.degraded === true,
    error: grounding.error ?? "",
    policy: grounding.policy ?? null,
    results: Array.isArray(grounding.results)
      ? grounding.results.map((item) => ({
          title: item.title ?? "",
          url: item.url ?? "",
          snippet: item.snippet ?? "",
          source: item.source ?? "",
        }))
      : [],
  };
}

function buildWebGroundingPolicyEntries(policy) {
  if (!policy || typeof policy !== "object") {
    return [];
  }

  return [
    { label: "Requested Results", value: String(policy.requested_max_results ?? 0) },
    { label: "Applied Results", value: String(policy.applied_max_results ?? 0) },
    { label: "Raw Results", value: String(policy.raw_result_count ?? 0) },
    { label: "Filtered Results", value: String(policy.filtered_result_count ?? 0) },
    { label: "Invalid URL Results", value: String(policy.invalid_result_count ?? 0) },
    { label: "Blocked Domain Results", value: String(policy.blocked_result_count ?? 0) },
    { label: "Allowlist Filtered", value: String(policy.allowlist_filtered_count ?? 0) },
  ];
}

function buildWebGroundingStatus(grounding) {
  if (grounding?.degraded) {
    return grounding?.queryTruncated
      ? "search degraded, query truncated by policy"
      : "search degraded";
  }
  if (grounding?.queryTruncated) {
    return "truncated by policy";
  }
  return "unchanged";
}

function formatWebSearchHealthLabel(webSearch) {
  if (!webSearch || typeof webSearch !== "object") {
    return "unknown";
  }
  const provider = typeof webSearch.provider === "string" && webSearch.provider.trim()
    ? webSearch.provider
    : "unknown";
  const status = typeof webSearch.status === "string" && webSearch.status.trim()
    ? webSearch.status
    : "unknown";
  return `${provider} - ${status}`;
}

function buildDebugSignalEntries(debugSignals) {
  if (!debugSignals || typeof debugSignals !== "object") {
    return [];
  }

  const entries = [];
  if (debugSignals.note_class) {
    entries.push({ label: "Note Class", value: String(debugSignals.note_class) });
  }
  if (debugSignals.final_score != null) {
    entries.push({ label: "Final Score", value: String(debugSignals.final_score) });
  }
  if (debugSignals.match_counts) {
    entries.push({
      label: "Match Counts",
      value: JSON.stringify(debugSignals.match_counts, null, 2),
    });
  }
  if (debugSignals.semantic) {
    entries.push({
      label: "Semantic",
      value: JSON.stringify(debugSignals.semantic, null, 2),
    });
  }
  if (debugSignals.bonuses) {
    entries.push({
      label: "Bonuses",
      value: JSON.stringify(debugSignals.bonuses, null, 2),
    });
  }
  if (debugSignals.penalties) {
    entries.push({
      label: "Penalties",
      value: JSON.stringify(debugSignals.penalties, null, 2),
    });
  }
  if (debugSignals.profile) {
    entries.push({
      label: "Profile",
      value: JSON.stringify(debugSignals.profile, null, 2),
    });
  }
  if (debugSignals.linked_from) {
    entries.push({
      label: "Linked From",
      value: Array.isArray(debugSignals.linked_from)
        ? debugSignals.linked_from.join("\n")
        : String(debugSignals.linked_from),
    });
  }
  if (debugSignals.related_adjustment) {
    entries.push({
      label: "Related Adjustment",
      value: JSON.stringify(debugSignals.related_adjustment, null, 2),
    });
  }
  if (debugSignals.graph) {
    entries.push({
      label: "Graph",
      value: JSON.stringify(debugSignals.graph, null, 2),
    });
  }
  if (debugSignals.reason_tags) {
    entries.push({
      label: "Reason Tags",
      value: Array.isArray(debugSignals.reason_tags)
        ? debugSignals.reason_tags.join("\n")
        : String(debugSignals.reason_tags),
    });
  }
  return entries;
}

function countBenchmarkTurns(resultPayload) {
  return Array.isArray(resultPayload?.turn_results) ? resultPayload.turn_results.length : 0;
}

function buildBenchmarkPreview(resultPayload) {
  if (!resultPayload || typeof resultPayload !== "object") {
    return "";
  }
  if (typeof resultPayload.answer_text === "string" && resultPayload.answer_text.trim()) {
    return resultPayload.answer_text;
  }
  if (typeof resultPayload.final_output === "string" && resultPayload.final_output.trim()) {
    return resultPayload.final_output;
  }
  if (typeof resultPayload.status === "string" && resultPayload.status.trim()) {
    return `Status: ${resultPayload.status}`;
  }
  return JSON.stringify(resultPayload, null, 2);
}

function buildUserMeta(composer) {
  return `${formatSelectedModelLabel(composer.model)} - ${composer.reasoningMode} - ${composer.scopeText}`;
}

function resolveApiModel(selectedModel) {
  return selectedModel === STANDARD_MODEL_VALUE ? undefined : selectedModel;
}

function formatSelectedModelLabel(selectedModel) {
  return selectedModel === STANDARD_MODEL_VALUE ? "Standard" : selectedModel;
}

function buildConversationHistory(messages) {
  return messages
    .map(convertMessageToConversationTurn)
    .filter(Boolean)
    .slice(-8);
}

function buildPreprocessRows(preprocess) {
  if (!preprocess || typeof preprocess !== "object") {
    return [];
  }

  const rows = [];
  const mode = typeof preprocess.mode === "string" ? preprocess.mode.trim() : "";
  const applied = preprocess.applied === true;
  const originalText = normalizePromptPreview(preprocess.original_text);
  const processedText = normalizePromptPreview(preprocess.processed_text);
  const translatorOutput = normalizePromptPreview(preprocess.translator_output);
  const translatorError = normalizePromptPreview(preprocess.translator_error);
  const fallbackReason = normalizePromptPreview(preprocess.fallback_reason);

  if (mode) {
    rows.push({
      label: "Status",
      value: applied
        ? `${mode} applied`
        : `${mode} ${fallbackReason || "fallback/no change"}`,
    });
  }
  if (originalText) {
    rows.push({ label: "Original", value: originalText });
  }
  if (processedText) {
    rows.push({ label: "Processed", value: processedText });
  }
  if (translatorOutput) {
    rows.push({ label: "Translator", value: translatorOutput });
  }
  if (translatorError) {
    rows.push({ label: "Translator Error", value: translatorError });
  }
  return rows;
}

function normalizePromptPreview(value) {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim();
}

function finalizeWorkflowResponse({ response, workflow, onProgress, stageTemplate, preprocess }) {
  const resolvedPreprocess = extractPreprocessPayload(response, preprocess);
  onProgress({
    status: "completed",
    summary: progressSummaryForWorkflow(workflow),
    meta: `${workflow} completed`,
    stages: finalizeStages(stageTemplate),
    preprocess: resolvedPreprocess,
  });
  return {
    result: response.result ?? response,
    execution: response.execution ?? response.result?.execution ?? null,
  };
}

function extractPreprocessPayload(response, fallback = null) {
  if (response?.preprocess && typeof response.preprocess === "object") {
    return response.preprocess;
  }
  if (response?.result?.preprocess && typeof response.result.preprocess === "object") {
    return response.result.preprocess;
  }
  return fallback;
}

function convertMessageToConversationTurn(message) {
  if (!message || message.kind === "progress" || (message.role !== "user" && message.role !== "assistant")) {
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
    return [
      message.payload.answer,
      ...(message.payload.summaryItems ?? []).map((item) => `${item.label}: ${item.value}`),
    ]
      .filter(Boolean)
      .join("\n");
  }

  if (message.kind === "draft") {
    return [message.payload.summary, message.payload.content].filter(Boolean).join("\n\n");
  }

  if (message.kind === "analyze") {
    return [message.payload.summary, ...(message.payload.suggestions ?? [])].filter(Boolean).join("\n");
  }

  if (message.kind === "benchmark") {
    return [message.payload.finalPreview, ...(message.payload.summaryItems ?? []).map((item) => `${item.label}: ${item.value}`)]
      .filter(Boolean)
      .join("\n");
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

function deriveDraftTitle(prompt) {
  return truncateText(prompt.replace(/\s+/g, " ").trim(), 42) || "Draft Note";
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

function composerPlaceholder() {
  return "Implement a parser for minishell redirections in C and ground the answer in my notes.";
}

function buildProgressStages(workflow) {
  if (workflow === "agent") {
    return [
      { title: "Routing request", detail: "Deciding the workflow and reasoning mode.", status: "pending" },
      { title: "Grounding context", detail: "Collecting retrieval context and repo hints.", status: "pending" },
      { title: "Planning and discussion", detail: "Planner, critic, synthesis, and approval loop.", status: "pending" },
      { title: "Executor summary", detail: "Finalizing task plan and actionable output.", status: "pending" },
    ];
  }

  if (workflow === "implementation") {
    return [
      { title: "Routing request", detail: "Classifying this as scoped implementation work.", status: "pending" },
      { title: "Grounding context", detail: "Loading notes and relevant implementation constraints.", status: "pending" },
      { title: "Scoping slices", detail: "Breaking the work into ordered, reviewable slices.", status: "pending" },
      { title: "Final answer", detail: "Returning the scoped implementation plan.", status: "pending" },
    ];
  }

  if (workflow === "draft") {
    return [
      { title: "Routing request", detail: "Selecting note drafting workflow.", status: "pending" },
      { title: "Grounding context", detail: "Collecting note context and vault constraints.", status: "pending" },
      { title: "Draft generation", detail: "Writing the note draft and proposal.", status: "pending" },
    ];
  }

  if (workflow === "analyze") {
    return [
      { title: "Routing request", detail: "Selecting directory analysis workflow.", status: "pending" },
      { title: "Directory scan", detail: "Inspecting note inventory and graph edges.", status: "pending" },
      { title: "Coverage report", detail: "Summarizing unresolved links and gaps.", status: "pending" },
    ];
  }

  return [
    { title: "Routing request", detail: "Choosing the grounded answer workflow.", status: "pending" },
    { title: "Grounding context", detail: "Collecting notes and related graph context.", status: "pending" },
    { title: "Answer synthesis", detail: "Producing the final coding-focused answer.", status: "pending" },
  ];
}

function progressSummaryForWorkflow(workflow) {
  if (workflow === "agent") {
    return "Running planner-first agent workflow.";
  }
  if (workflow === "implementation") {
    return "Scoping the request into safe implementation slices.";
  }
  if (workflow === "draft") {
    return "Drafting a grounded note proposal.";
  }
  if (workflow === "analyze") {
    return "Analyzing directory structure and graph coverage.";
  }
  return "Preparing a grounded coding answer.";
}

function markStagesActive(stages, activeIndex) {
  return stages.map((stage, index) => {
    if (index < activeIndex) {
      return { ...stage, status: "completed" };
    }
    if (index === activeIndex) {
      return { ...stage, status: "running" };
    }
    return { ...stage, status: "pending" };
  });
}

function finalizeStages(stages) {
  return stages.map((stage) => ({ ...stage, status: "completed" }));
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

function getLatestProgressMessage(messages) {
  return [...messages].reverse().find((message) => message.kind === "progress") ?? null;
}

function getCurrentProgressStage(stages) {
  return stages.find((stage) => stage.status === "running")
    ?? [...stages].reverse().find((stage) => stage.status === "completed")
    ?? null;
}

export default App;
