import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

function CodeBlock({ node, inline, className, children, ...props }) {
  const match = /language-(\w+)/.exec(className || '')
  return !inline && match ? (
    <SyntaxHighlighter
      style={oneDark}
      language={match[1]}
      PreTag="div"
      customStyle={{
        margin: 0,
        borderRadius: '8px',
        fontSize: '13px',
        background: '#0d0d0f',
      }}
      {...props}
    >
      {String(children).replace(/\n$/, '')}
    </SyntaxHighlighter>
  ) : (
    <code className={className} {...props}>{children}</code>
  )
}

export default function Message({ role, content, model, isStreaming }) {
  const isUser = role === 'user'

  return (
    <div className={`message ${role}`}>
      <div className={`avatar ${role}`}>
        {isUser ? '👤' : '✦'}
      </div>
      <div className="message-body">
        <div className="message-meta">
          {isUser ? 'You' : 'Prayāsa'}
          {model && !isUser && (
            <span style={{ opacity: 0.5 }}>{model.split('/').pop()}</span>
          )}
        </div>
        <div className="message-content">
          {isUser ? (
            <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
          ) : (
            <>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{ code: CodeBlock }}
              >
                {content}
              </ReactMarkdown>
              {isStreaming && <span className="cursor" />}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
