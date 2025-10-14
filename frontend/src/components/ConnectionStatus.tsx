import React, { useState, useEffect } from 'react';
import { Alert, Button } from 'antd';
import { ExclamationCircleOutlined, CheckCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { apiClient, ApiError } from '../api';

interface ConnectionStatusProps {
  onStatusChange?: (isConnected: boolean) => void;
}

export default function ConnectionStatus({ onStatusChange }: ConnectionStatusProps) {
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkConnection = async () => {
    setIsChecking(true);
    setError(null);

    try {
      await apiClient.healthCheck();
      setIsConnected(true);
      onStatusChange?.(true);
    } catch (err) {
      setIsConnected(false);
      onStatusChange?.(false);
      
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Error de conexión desconocido');
      }
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkConnection();
  }, []);

  if (isConnected === true) {
    return null;
  }

  if (isConnected === null && isChecking) {
    return (
      <Alert
        message="Verificando conexión con el servidor..."
        type="info"
        showIcon
        icon={<ReloadOutlined spin />}
        style={{ margin: 16 }}
      />
    );
  }

  if (isConnected === false) {
    return (
      <Alert
        message="Error de conexión"
        description={
          <div>
            <p>{error || 'No se puede conectar al servidor de la API legal.'}</p>
            <Button 
              type="primary" 
              size="small" 
              icon={<ReloadOutlined />}
              loading={isChecking}
              onClick={checkConnection}
            >
              Reintentar conexión
            </Button>
          </div>
        }
        type="error"
        showIcon
        icon={<ExclamationCircleOutlined />}
        style={{ margin: 16 }}
      />
    );
  }

  return null;
}