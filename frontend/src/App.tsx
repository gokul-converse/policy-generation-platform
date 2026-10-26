import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

type ServerResponse = {
  event?: string;
  type?: string;
  session_id?: string;
  requirement_id?: string;
  question?: string;
  message?: string;
  content?: string;
  error?: string;
  detail?: string;
  draft?: Record<string, unknown>;
  requirements?: Record<string, unknown>;
  version_number?: number;
  version_id?: string;
  [key: string]: unknown;
};

type ChatMessage = {
  role: "user" | "assistant" | "system";
  text: string;
  kind?: "draft" | "success" | "error";
  data?: ServerResponse;
};

const WS_URL =
  (import.meta.env.VITE_REQUIREMENT_WS_URL as string | undefined) ||
  "ws://localhost:8000/ws/requirements";

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Hi! Tell me what requirement or policy you want to create. I’ll ask clarification questions and prepare a draft for you to review.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ServerResponse | null>(null);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [canAnswer, setCanAnswer] = useState(false);
  const [error, setError] = useState("");
  const socketRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy, draft]);

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  function addMessage(message: ChatMessage) {
    setMessages((previous) => [...previous, message]);
  }

  function connect(): Promise<WebSocket> {
    const current = socketRef.current;
    if (current?.readyState === WebSocket.OPEN) return Promise.resolve(current);

    return new Promise((resolve, reject) => {
      setError("");
      const socket = new WebSocket(WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        setConnected(true);
        resolve(socket);
      };

      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
      };

      socket.onerror = () => {
        setConnected(false);
        setError(`Cannot connect. Check that FastAPI is running at ${WS_URL}`);
        reject(new Error("WebSocket connection failed"));
      };

      socket.onmessage = (event) => {
        try {
          handleResponse(JSON.parse(event.data) as ServerResponse);
        } catch {
          setBusy(false);
          setError("Backend response was not valid JSON.");
        }
      };
    });
  }

  function handleResponse(response: ServerResponse) {
    const eventName = response.event || response.type || "";

    if (response.session_id) setSessionId(response.session_id);
    setBusy(false);
    setError("");

    if (eventName === "clarification_question") {
      setDraft(null);
      setCanAnswer(true);
      addMessage({
        role: "assistant",
        text: response.question || response.message || "Please provide more details.",
      });
      return;
    }

    if (eventName === "requirement_draft") {
      setCanAnswer(false);
      setDraft(response);
      addMessage({
        role: "assistant",
        text: "Your requirement draft is ready. Review it below before confirming.",
        kind: "draft",
        data: response,
      });
      return;
    }

    if (eventName === "requirements_finalized") {
      setCanAnswer(false);
      setDraft(null);
      addMessage({
        role: "assistant",
        text: response.version_number
          ? `Requirements confirmed successfully. Version ${response.version_number} created.`
          : "Requirements confirmed successfully.",
        kind: "success",
        data: response,
      });
      return;
    }

    if (eventName === "error" || response.error || response.detail) {
      setError(response.error || response.detail || response.message || "Backend error.");
      return;
    }

    addMessage({
      role: "assistant",
      text: response.message || response.content || `Received response: ${eventName || "unknown event"}`,
    });
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    setInput("");
    setError("");
    setBusy(true);
    addMessage({ role: "user", text });

    try {
      const socket = await connect();

      if (!sessionId) {
        socket.send(JSON.stringify({ event: "start", message: text }));
      } else if (canAnswer) {
        socket.send(JSON.stringify({ event: "answer", session_id: sessionId, message: text }));
        setCanAnswer(false);
      } else {
        setBusy(false);
        setError("Please wait for the next question, or start a new conversation.");
      }
    } catch {
      setBusy(false);
    }
  }

  function confirmDraft() {
    if (!sessionId || !draft || busy) return;
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError("WebSocket disconnected. Please reconnect and try again.");
      return;
    }
    setBusy(true);
    setError("");
    socket.send(JSON.stringify({
      event: "confirm",
      session_id: sessionId,
      message: "confirm",
    }));
  }

  function cancelSession() {
    const socket = socketRef.current;
    if (sessionId && socket?.readyState === WebSocket.OPEN && !busy) {
      setBusy(true);
      socket.send(JSON.stringify({
        event: "cancel",
        session_id: sessionId,
        message: "cancel",
      }));
    }
    setSessionId(null);
    setDraft(null);
    setCanAnswer(false);
    setBusy(false);
    setMessages([{
      role: "assistant",
      text: "New conversation. What requirement or policy would you like to create?",
    }]);
    setError("");
  }

  function draftFields() {
    if (!draft) return null;
    const details = (draft.draft || draft.requirements || {}) as Record<string, unknown>;
    const entries = Object.entries(details).filter(([, value]) => value !== null && value !== undefined);
    if (!entries.length) {
      return <pre>{JSON.stringify(draft, null, 2)}</pre>;
    }
    return entries.map(([key, value]) => (
      <div className="draft-field" key={key}>
        <strong>{key.replace(/_/g, " ")}</strong>
        <p>{Array.isArray(value) ? value.map(String).join("\n") : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value || "Not specified")}</p>
      </div>
    ));
  }

  return (
    <main className="page">
      <header className="topbar">
        <div className="logo">R</div>
        <div>
          <h1>Requirement Chatbot</h1>
          <p>Gather · Validate · Confirm</p>
        </div>
        <div className={`status ${connected ? "online" : ""}`}>
          <span />{connected ? "Connected" : "Disconnected"}
        </div>
        <button className="new-button" onClick={cancelSession}>New chat</button>
      </header>

      <section className="chat-card">
        <div className="chat-heading">
          <div>
            <h2>Requirement assistant</h2>
            <p>{sessionId ? `Session: ${sessionId}` : "Describe your requirement to get started"}</p>
          </div>
        </div>

        <div className="messages">
          {messages.map((message, index) => (
            <div className={`message-row ${message.role}`} key={`${index}-${message.text.slice(0, 12)}`}>
              <div className="bubble">
                {message.text}
                {message.kind === "success" && message.data?.version_id && (
                  <small className="version">Version ID: {String(message.data.version_id)}</small>
                )}
              </div>
            </div>
          ))}
          {busy && <div className="message-row assistant"><div className="bubble typing">Assistant is thinking…</div></div>}
          <div ref={bottomRef} />
        </div>

        {draft && (
          <div className="draft-card">
            <h3>Requirement draft</h3>
            <p className="draft-note">Review the details. Confirm only when you are ready.</p>
            <div className="draft-fields">{draftFields()}</div>
            <button className="confirm-button" onClick={confirmDraft} disabled={busy}>
              {busy ? "Confirming…" : "Confirm requirements"}
            </button>
          </div>
        )}

        {error && <div className="error">{error}</div>}

        <form className="composer" onSubmit={send}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder={canAnswer ? "Type your answer…" : "Describe your requirement…"}
            rows={2}
            disabled={busy || Boolean(draft)}
          />
          <button type="submit" disabled={!input.trim() || busy || Boolean(draft)}>
            Send
          </button>
        </form>
        <p className="hint">Enter to send · Shift + Enter for a new line</p>
      </section>
      <footer>Sample frontend connected to your FastAPI WebSocket backend</footer>
    </main>
  );
}
