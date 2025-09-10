import React from 'react';
import { Button, Space, Avatar, Typography, Flex, Spin, Alert } from 'antd';
import {
  CopyOutlined,
  DownloadOutlined,
  LikeOutlined,
  DislikeOutlined,
  UserOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { Message } from '../api';
import SourcesList from './SourcesList';
import MarkdownRenderer from './MarkdownRenderer';

const { Text } = Typography;

interface MessageBubbleProps {
  message: Message;
  onCopy?: (content: string) => void;
  onLike?: (message: Message) => void;
  onDislike?: (message: Message) => void;
}

export default function MessageBubble({ 
  message, 
  onCopy, 
  onLike, 
  onDislike 
}: MessageBubbleProps) {
  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    onCopy?.(message.content);
  };

  return (
    <Flex
      gap={8}
      align="flex-start"
      style={{
        maxWidth: '85%',
        alignSelf: message.role === "user" ? 'flex-end' : 'flex-start',
        flexDirection: message.role === "user" ? 'row-reverse' : 'row'
      }}
    >
      {message.role === "agent" && (
        <Avatar 
          size={32} 
          style={{ backgroundColor: '#1890ff', flexShrink: 0 }}
        >
          L
        </Avatar>
      )}
      {message.role === "user" && (
        <Avatar 
          size={32} 
          icon={<UserOutlined />}
          style={{ flexShrink: 0 }}
        />
      )}
      
      <div style={{ flex: 1, minWidth: 0 }}>
        <Flex 
          gap={8} 
          align="center" 
          style={{ 
            marginBottom: 4,
            flexDirection: message.role === "user" ? 'row-reverse' : 'row'
          }}
        >
          <Text strong style={{ fontSize: 12 }}>
            {message.role === "agent" ? "Asistente Legal" : "Usuario"}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {message.timestamp}
          </Text>
        </Flex>
        
        <div style={{ 
          padding: 12, 
          backgroundColor: message.role === "user" ? '#e6f7ff' : '#f5f5f5', 
          borderRadius: 8,
          marginBottom: message.role === "agent" ? 8 : 0
        }}>
          {message.isLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Spin size="small" />
              <Text style={{ fontSize: 12, color: '#666' }}>
                Consultando la base de datos legal...
              </Text>
            </div>
          ) : message.error ? (
            <Alert
              message="Error en la consulta"
              description={message.error}
              type="error"
              icon={<ExclamationCircleOutlined />}
            />
          ) : message.role === 'agent' ? (
            <MarkdownRenderer content={message.content} />
          ) : (
            <Text style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>
              {message.content}
            </Text>
          )}
        </div>
        
        {message.role === "agent" && !message.isLoading && !message.error && (
          <>
            <Space size={4}>
              <Button 
                type="text" 
                size="small" 
                icon={<CopyOutlined />} 
                onClick={handleCopy}
                style={{ height: 32, width: 32, padding: 0 }}
                title="Copiar respuesta"
              />
              <Button 
                type="text" 
                size="small" 
                icon={<DownloadOutlined />}
                style={{ height: 32, width: 32, padding: 0 }}
                title="Descargar"
              />
              <Button 
                type="text" 
                size="small" 
                icon={<LikeOutlined />}
                onClick={() => onLike?.(message)}
                style={{ height: 32, width: 32, padding: 0 }}
                title="Me gusta"
              />
              <Button 
                type="text" 
                size="small" 
                icon={<DislikeOutlined />}
                onClick={() => onDislike?.(message)}
                style={{ height: 32, width: 32, padding: 0 }}
                title="No me gusta"
              />
            </Space>
            
            {message.sources && message.sources.length > 0 && (
              <SourcesList 
                sources={message.sources} 
                processingTime={message.processing_time}
                documentsFound={message.documents_found}
              />
            )}
          </>
        )}
      </div>
    </Flex>
  );
}