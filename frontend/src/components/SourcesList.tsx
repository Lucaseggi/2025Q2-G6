import React from 'react';
import { Card, Tag, Typography, Space, Divider } from 'antd';
import { BookOutlined, CalendarOutlined, TrophyOutlined } from '@ant-design/icons';
import { ApiSource } from '../api';

const { Text, Link } = Typography;

interface SourcesListProps {
  sources: ApiSource[];
  processingTime?: number;
  documentsFound?: number;
}

export default function SourcesList({ sources, processingTime, documentsFound }: SourcesListProps) {
  if (!sources.length) return null;

  return (
    <Card 
      size="small"
      title={
        <Space>
          <BookOutlined />
          <Text strong>
            Fuentes consultadas ({sources.length}
            {documentsFound && documentsFound > sources.length && ` de ${documentsFound}`})
          </Text>
        </Space>
      }
      style={{ marginTop: 8 }}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        {sources.map((source, index) => (
          <div key={source.id || index}>
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <div>
                <Link strong style={{ fontSize: 12 }}>
                  {source.title}
                </Link>
                <div style={{ marginTop: 2 }}>
                  <Space size={8}>
                    <Tag color="blue" style={{ fontSize: 10, padding: '0 4px' }}>
                      {source.type}
                    </Tag>
                    {source.date && (
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        <CalendarOutlined style={{ marginRight: 2 }} />
                        {new Date(source.date).toLocaleDateString('es-AR')}
                      </Text>
                    )}
                    <Text type="secondary" style={{ fontSize: 10 }}>
                      <TrophyOutlined style={{ marginRight: 2 }} />
                      {(source.score * 100).toFixed(1)}% relevancia
                    </Text>
                  </Space>
                </div>
              </div>
            </Space>
            {index < sources.length - 1 && <Divider style={{ margin: '8px 0' }} />}
          </div>
        ))}
        
        {(processingTime || documentsFound) && (
          <>
            <Divider style={{ margin: '8px 0' }} />
            <Space size={16}>
              {processingTime && (
                <Text type="secondary" style={{ fontSize: 10 }}>
                  Procesado en {processingTime.toFixed(2)}s
                </Text>
              )}
              {documentsFound && (
                <Text type="secondary" style={{ fontSize: 10 }}>
                  {documentsFound} documentos encontrados
                </Text>
              )}
            </Space>
          </>
        )}
      </Space>
    </Card>
  );
}