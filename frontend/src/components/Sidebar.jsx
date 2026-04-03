export default function Sidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  activeModel,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-dot" />
          Prayāsa
        </div>
        <button className="new-chat-btn" onClick={onNewChat}>
          <span>＋</span> New Chat
        </button>
      </div>

      {sessions.length > 0 && (
        <div className="sidebar-section-label">Recent</div>
      )}

      <div className="sessions-list">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`session-item ${s.id === activeSessionId ? 'active' : ''}`}
            onClick={() => onSelectSession(s.id)}
          >
            <span className="session-title">{s.title || 'New Chat'}</span>
            <button
              className="session-delete"
              onClick={(e) => {
                e.stopPropagation()
                onDeleteSession(s.id)
              }}
              title="Delete"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="model-badge">
          {activeModel === 'auto' ? 'auto-routing' : activeModel?.split('/').pop()}
        </div>
      </div>
    </aside>
  )
}
