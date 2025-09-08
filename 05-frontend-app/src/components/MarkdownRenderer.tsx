import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Typography } from 'antd';

const { Text } = Typography;

interface MarkdownRendererProps {
  content: string;
  style?: React.CSSProperties;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, style }) => {
  return (
    <div style={style}>
      <ReactMarkdown
        components={{
          p: ({ children }) => (
            <Text style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              {children}
            </Text>
          ),
          strong: ({ children }) => (
            <Text strong style={{ fontSize: 12 }}>
              {children}
            </Text>
          ),
          em: ({ children }) => (
            <Text italic style={{ fontSize: 12 }}>
              {children}
            </Text>
          ),
          del: ({ children }) => (
            <Text delete style={{ fontSize: 12 }}>
              {children}
            </Text>
          ),
          ul: ({ children }) => (
            <ul style={{ fontSize: 12, marginLeft: 16, marginBottom: 8 }}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol style={{ fontSize: 12, marginLeft: 16, marginBottom: 8 }}>
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li style={{ fontSize: 12, marginBottom: 4 }}>
              {children}
            </li>
          ),
          code: ({ children }) => (
            <Text code style={{ fontSize: 11 }}>
              {children}
            </Text>
          ),
          blockquote: ({ children }) => (
            <div style={{ 
              borderLeft: '3px solid #d9d9d9', 
              paddingLeft: 12, 
              margin: '8px 0',
              fontStyle: 'italic',
              fontSize: 12
            }}>
              {children}
            </div>
          ),
          h1: ({ children }) => (
            <Text strong style={{ fontSize: 16, display: 'block', marginBottom: 8 }}>
              {children}
            </Text>
          ),
          h2: ({ children }) => (
            <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 6 }}>
              {children}
            </Text>
          ),
          h3: ({ children }) => (
            <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
              {children}
            </Text>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;