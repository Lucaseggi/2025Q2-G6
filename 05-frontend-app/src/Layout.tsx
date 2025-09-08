import React from 'react';
import { Layout as AntLayout, Menu, Button, Space } from 'antd';
import {
  AppstoreOutlined,
  FunctionOutlined,
  ApiOutlined,
  UsergroupAddOutlined,
  SettingOutlined,
  EyeOutlined,
  BarChartOutlined,
  SaveOutlined,
  CloseOutlined
} from '@ant-design/icons';

const { Sider, Header, Content } = AntLayout;

export default function Layout({ children }: { children: React.ReactNode }) {
  const menuItems = [
    {
      key: 'tasks',
      icon: <AppstoreOutlined />,
      label: 'Tasks',
    },
    {
      key: 'functions',
      icon: <FunctionOutlined />,
      label: 'Functions',
    },
    {
      key: 'integrations',
      icon: <ApiOutlined />,
      label: 'Integrations',
    },
    {
      key: 'users',
      icon: <UsergroupAddOutlined />,
      label: 'Users',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ];

  const secondaryMenuItems = [
    {
      key: 'live-preview',
      icon: <EyeOutlined />,
      label: 'Live preview',
    },
    {
      key: 'performance',
      icon: <BarChartOutlined />,
      label: 'Performance',
    },
  ];

  return (
    <AntLayout style={{ height: '100vh' }}>
      {/* Sidebar */}
      <Sider width={256} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
          <Space align="center">
            <div style={{ 
              width: 24, 
              height: 24, 
              borderRadius: '50%', 
              backgroundColor: '#1890ff' 
            }} />
            <span style={{ fontWeight: 600 }}>Simpla Legal</span>
          </Space>
        </div>
        <div style={{ padding: '16px 0' }}>
          <Menu
            mode="inline"
            items={menuItems}
            style={{ border: 'none', marginBottom: 16 }}
          />
          <div style={{ 
            borderTop: '1px solid #f0f0f0', 
            paddingTop: 16, 
            marginTop: 16 
          }}>
            <Menu
              mode="inline"
              items={secondaryMenuItems}
              style={{ border: 'none' }}
            />
          </div>
        </div>
      </Sider>

      <AntLayout>
        {/* Header */}
        <Header style={{ 
          background: '#fff', 
          borderBottom: '1px solid #f0f0f0', 
          padding: '0 16px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          height: 56
        }}>
          <h1 style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>
            Consulta Legal RAG
          </h1>
          <Space>
            <Button type="text" icon={<SaveOutlined />}>
              Guardar conversación
            </Button>
            <Button type="text" icon={<CloseOutlined />} />
          </Space>
        </Header>

        <AntLayout>
          {/* Main Content */}
          <Content style={{ display: 'flex', flexDirection: 'column' }}>
            {children}
          </Content>

          {/* Right Panel */}
          <Sider 
            width={320} 
            theme="light" 
            style={{ borderLeft: '1px solid #f0f0f0' }}
          >
            <div style={{ 
              height: 56, 
              borderBottom: '1px solid #f0f0f0', 
              padding: '0 16px', 
              display: 'flex', 
              alignItems: 'center' 
            }}>
              <h2 style={{ margin: 0, fontWeight: 500 }}>Conversation details</h2>
            </div>
            <div style={{ padding: 16 }}>
              <Space style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 16 }}>
                <Button type="primary" shape="round" size="small">
                  Actions
                </Button>
                <Button type="text" shape="round" size="small">
                  Customer
                </Button>
                <Button type="text" shape="round" size="small">
                  Settings
                </Button>
              </Space>
            </div>
          </Sider>
        </AntLayout>
      </AntLayout>
    </AntLayout>
  )
}
