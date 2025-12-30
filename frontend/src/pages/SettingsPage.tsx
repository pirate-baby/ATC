import { useState } from 'react'
import { ClaudeTokenSettings } from '../components/ClaudeTokenSettings'
import { PoolStatus } from '../components/PoolStatus'

type SettingsTab = 'claude-token' | 'pool-status'

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('claude-token')

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h2>Settings</h2>
          <p className="page-subtitle">
            Manage your account settings and view pool status
          </p>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'claude-token' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('claude-token')}
        >
          Claude Token
        </button>
        <button
          className={`tab ${activeTab === 'pool-status' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('pool-status')}
        >
          Pool Status
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'claude-token' && <ClaudeTokenSettings />}
        {activeTab === 'pool-status' && <PoolStatus />}
      </div>
    </div>
  )
}
