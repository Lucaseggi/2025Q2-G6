import React, { useState, useCallback, useRef, useEffect } from "react";
import { Button, Input, message as antMessage, Alert } from "antd";
import { SendOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import { apiClient, ApiError, Message } from "./api";
import { MessageBubble, ConnectionStatus } from "./components";

const { TextArea } = Input;

export default function ChatInterface() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      content: "¡Hola! Soy tu asistente legal especializado en normativa argentina. Puedes hacerme cualquier pregunta sobre leyes, decretos, regulaciones y otros documentos legales del país. ¿En qué puedo ayudarte hoy?",
      timestamp: new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTimestamp = () => {
    return new Date().toLocaleTimeString('es-AR', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit' 
    });
  };

  const handleSendMessage = useCallback(async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    const timestamp = formatTimestamp();
    const userMessage: Message = {
      role: "user",
      content: question,
      timestamp
    };

    // Add user message
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setApiError(null);

    // Add loading message
    const loadingMessage: Message = {
      role: "agent",
      content: "",
      timestamp: formatTimestamp(),
      isLoading: true
    };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      const response = await apiClient.askQuestion({ question });
      
      // Replace loading message with response
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = {
          role: "agent",
          content: response.answer,
          timestamp: formatTimestamp(),
          sources: response.sources,
          processing_time: response.processing_time,
          documents_found: response.documents_found,
          isLoading: false
        };
        return newMessages;
      });
      
      antMessage.success('Consulta procesada exitosamente');
    } catch (error) {
      let errorMessage = 'Error desconocido';
      let fallbackContent = '';
      
      if (error instanceof ApiError) {
        errorMessage = error.message;
        if (error.fallbackAnswer) {
          fallbackContent = error.fallbackAnswer;
        }
        
        // Set global error for connection issues
        if (error.status === 0) {
          setApiError(error.message);
        }
      } else {
        errorMessage = 'Error de conexión inesperado';
        setApiError('No se puede conectar con el servidor');
      }
      
      // Replace loading message with error message
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = {
          role: "agent",
          content: fallbackContent || `Lo siento, ocurrió un error al procesar tu consulta: ${errorMessage}`,
          timestamp: formatTimestamp(),
          error: errorMessage,
          isLoading: false
        };
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCopy = useCallback(() => {
    antMessage.success('Respuesta copiada al portapapeles');
  }, []);

  const handleLike = useCallback((message: Message) => {
    antMessage.info('Gracias por tu feedback positivo');
  }, []);

  const handleDislike = useCallback((message: Message) => {
    antMessage.info('Gracias por tu feedback, lo tendremos en cuenta');
  }, []);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <ConnectionStatus onStatusChange={setIsConnected} />
      
      {apiError && (
        <Alert
          message="Error de conexión"
          description={apiError}
          type="error"
          closable
          onClose={() => setApiError(null)}
          icon={<ExclamationCircleOutlined />}
          style={{ margin: 16 }}
        />
      )}
      
      <div 
        style={{ 
          flex: 1, 
          padding: 16, 
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16
        }}
      >
        {messages.map((message, index) => (
          <MessageBubble
            key={index}
            message={message}
            onCopy={handleCopy}
            onLike={handleLike}
            onDislike={handleDislike}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div style={{ 
        padding: 16, 
        borderTop: '1px solid #f0f0f0',
        backgroundColor: '#fff'
      }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <TextArea
            placeholder="Escribe tu consulta legal aquí... (Ej: ¿Cuáles son los derechos del trabajador?)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
            disabled={isLoading || !isConnected}
            maxLength={2000}
            showCount
          />
          <Button 
            type="primary" 
            icon={<SendOutlined />}
            onClick={handleSendMessage}
            loading={isLoading}
            disabled={!input.trim() || isLoading || !isConnected}
            style={{ alignSelf: 'flex-end' }}
          >
            {isLoading ? 'Enviando...' : 'Enviar'}
          </Button>
        </div>
      </div>
    </div>
  );
}
