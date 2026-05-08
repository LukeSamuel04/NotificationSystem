// src/pages/AccountSettingPage.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/http';
import {
  Plus, Mail, Camera, MessageSquare, Trash2, Power,
  Settings, Loader2, AlertCircle, ExternalLink, ChevronRight
} from 'lucide-react';
import type { AccountResponse } from '../types/account';

const AccountSettingPage: React.FC = () => {
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const defaultForm = {
    platform: 'email' as const,
    platform_account_id: '',
    username: '',
    password: '',
    is_active: true,
    config: {} as any
  };
  const [formData, setFormData] = useState<any>(defaultForm);

  const fetchAccounts = async () => {
    try {
      const res = await apiClient.get('/api/accounts');
      setAccounts(res.data);
    } catch (err) {
      console.error("加载账号失败", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleOpenAdd = () => {
    setEditingId(null);
    setFormData(defaultForm);
    setErrorMsg(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (account: AccountResponse) => {
    setEditingId(account.id);
    setFormData({
      platform: account.platform,
      platform_account_id: account.platform_account_id || '',
      username: account.username,
      password: '',
      is_active: account.is_active,
      config: account.config || {}
    });
    setErrorMsg(null);
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setErrorMsg(null);
    try {
      if (editingId) {
        await apiClient.put(`/api/accounts/${editingId}/`, formData);
      } else {
        await apiClient.post('/api/accounts/', formData);
      }
      setIsModalOpen(false);
      fetchAccounts();
    } catch (err: any) {
      const backendError = err.response?.data?.detail || "保存失败，请检查账号配置或网络";
      setErrorMsg(backendError);
    } finally {
      setIsSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteConfirmId) return;
    try {
      await apiClient.delete(`/api/accounts/${deleteConfirmId}/`);
      setDeleteConfirmId(null);
      setIsModalOpen(false);
      fetchAccounts();
    } catch (err) {
      alert("删除失败！");
    }
  };

  const simulateMetaAuth = () => {
    const mockToken = prompt("请输入 Page Access Token (EAA...):");
    const mockId = prompt("请输入 Instagram Business Account ID (1784...):");
    const mockUser = prompt("请输入 Instagram 用户名 (如 lss_sssal):");

    if (mockToken && mockId && mockUser) {
      setFormData({
        ...formData,
        platform: 'instagram',
        platform_account_id: mockId,
        username: mockUser,
        config: { ...formData.config, access_token: mockToken }
      });
    }
  };

  const handlePlatformChange = (platform: 'email' | 'instagram' | 'whatsapp') => {
    const base = { ...defaultForm, platform, is_active: formData.is_active };
    if (platform === 'email') {
      setFormData({ ...base, config: { host: '' } });
    } else if (platform === 'instagram') {
      setFormData({ ...base, config: { access_token: '', proxy_url: '' } });
    } else {
      setFormData({ ...base, config: { api_key: '' } });
    }
  };

  return (
    <>
      <style>{`
        /* 💥 核心修复 1: 确保页面作为独立可滚动区域，且占据 100% 剩余宽度 */
        .account-page { 
          height: 100vh; 
          width: 100%;
          background-color: #f8fafc; 
          font-family: 'Inter', system-ui, -apple-system, sans-serif;
          overflow-y: auto; /* 强制允许垂直滚动 */
          display: flex;
          flex-direction: column;
        }

        /* 💥 核心修复 2: 容器宽度放开，适配侧边栏后的剩余空间 */
        .account-container { 
          width: 100%;
          max-width: 1400px; /* 提升上限 */
          margin: 0 auto;
          padding: 48px 40px;
          box-sizing: border-box;
        }

        .account-header { 
          display: flex; 
          justify-content: space-between; 
          align-items: center; 
          margin-bottom: 40px;
          gap: 20px;
        }

        .account-header h1 { font-size: 32px; font-weight: 800; color: #1e293b; margin: 0; }
        .account-header p { color: #64748b; margin: 8px 0 0 0; font-size: 16px; }

        /* 💥 核心修复 3: 多列网格逻辑优化，降低最小宽度以强制分列 */
        .account-grid { 
          display: grid; 
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
          gap: 24px; 
          width: 100%;
        }

        .account-card { 
          background: white; 
          border: 1px solid #e2e8f0; 
          border-radius: 16px; 
          padding: 24px; 
          display: flex;
          flex-direction: column;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          transition: all 0.2s ease;
          min-height: 220px;
        }

        .account-card:hover { 
          transform: translateY(-2px);
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
          border-color: #4f46e5;
        }

        .card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
        
        .platform-icon { 
          padding: 10px; 
          border-radius: 12px; 
          background-color: #f1f5f9; 
          display: flex; 
          align-items: center; 
          justify-content: center;
        }

        .status-badge { 
          display: flex; 
          align-items: center; 
          gap: 6px; 
          font-size: 11px; 
          font-weight: 700; 
          padding: 4px 10px; 
          border-radius: 8px;
        }
        .status-active { background-color: #dcfce7; color: #166534; }
        .status-inactive { background-color: #f1f5f9; color: #475569; }
        .status-error { background-color: #fef2f2; color: #991b1b; }

        .account-info-main { flex-grow: 1; }
        .account-username { margin: 0 0 4px 0; font-size: 18px; font-weight: 700; color: #0f172a; word-break: break-all; }
        .account-platform { 
          font-size: 12px; 
          font-weight: 600;
          color: #94a3b8; 
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 12px;
          display: block;
        }
        
        .account-id-tag { 
          font-family: monospace; 
          font-size: 11px; 
          color: #64748b; 
          background: #f8fafc;
          padding: 4px 8px;
          border-radius: 4px;
          border: 1px solid #f1f5f9;
          display: block;
          margin-top: 8px;
        }
        
        .card-actions { 
          display: flex; 
          justify-content: space-between; 
          align-items: center;
          margin-top: 20px; 
          padding-top: 16px;
          border-top: 1px solid #f1f5f9; 
        }

        .action-link { 
          color: #4f46e5; 
          font-size: 13px; 
          font-weight: 600; 
          display: flex; 
          align-items: center; 
          gap: 4px; 
          cursor: pointer;
        }

        .btn { display: flex; align-items: center; gap: 8px; padding: 10px 18px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; }
        .btn-primary { background-color: #4f46e5; color: white; }
        .btn-primary:hover:not(:disabled) { background-color: #4338ca; }

        /* Modal 内容过长时的内部滚动控制 */
        .modal-overlay { position: fixed; inset: 0; background-color: rgba(0, 0, 0, 0.5); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 100; }
        .modal-content { 
          background: white; 
          border-radius: 20px; 
          padding: 32px; 
          width: 90%; 
          max-width: 460px; 
          max-height: 85vh; 
          overflow-y: auto; 
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); 
        }

        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 8px; }
        .form-control { width: 100%; padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; box-sizing: border-box; }
        .form-control:focus { border-color: #4f46e5; outline: none; }

        .toggle-switch { width: 48px; height: 26px; border-radius: 99px; position: relative; cursor: pointer; border: none; transition: background 0.2s; }
        .toggle-switch-on { background-color: #10b981; }
        .toggle-switch-off { background-color: #cbd5e1; }
        .toggle-knob { width: 20px; height: 20px; background: white; border-radius: 50%; position: absolute; top: 3px; transition: left 0.2s; }
      `}</style>

      <div className="account-page">
        <div className="account-container">
          <header className="account-header">
            <div>
              <h1>账号集成</h1>
              <p>当前系统规模 {accounts.length} 个端点</p>
            </div>
            <button className="btn btn-primary" onClick={handleOpenAdd}>
              <Plus size={18} /> 添加新账号
            </button>
          </header>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '100px 0' }}>
              <Loader2 className="animate-spin text-indigo-600" size={40} />
            </div>
          ) : (
            <div className="account-grid">
              {Array.isArray(accounts) && accounts.map(account => (
                <div key={account.id} className="account-card">
                  <div className="card-top">
                    <div className="platform-icon">
                      {account.platform === 'email' && <Mail color="#4f46e5" size={24} />}
                      {account.platform === 'instagram' && <Camera color="#db2777" size={24} />}
                      {account.platform === 'whatsapp' && <MessageSquare color="#16a34a" size={24} />}
                    </div>

                    <div className={`status-badge ${!account.is_active ? 'status-inactive' : account.is_valid ? 'status-active' : 'status-error'}`}>
                      <Power size={12} strokeWidth={3} />
                      {!account.is_active ? '已暂停' : account.is_valid ? '正常' : '故障'}
                    </div>
                  </div>

                  <div className="account-info-main">
                    <span className="account-platform">{account.platform} Protocol</span>
                    <h3 className="account-username">{account.username}</h3>
                    {account.platform_account_id && (
                      <code className="account-id-tag">UID: {account.platform_account_id}</code>
                    )}
                  </div>

                  <div className="card-actions">
                    <span className="action-link" onClick={() => handleOpenEdit(account)}>
                      配置详情 <ChevronRight size={14} />
                    </span>
                    <Settings className="text-slate-300" size={18} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {isModalOpen && (
          <div className="modal-overlay">
            <div className="modal-content">
              <h2 style={{ fontSize: '22px', fontWeight: 800, marginBottom: '24px' }}>
                {editingId ? '编辑账号' : '连接新平台'}
              </h2>

              {errorMsg && (
                <div style={{ background: '#fef2f2', color: '#991b1b', padding: '12px', borderRadius: '8px', marginBottom: '20px', fontSize: '13px', border: '1px solid #fecaca' }}>
                  {errorMsg}
                </div>
              )}

              <div className="form-group" style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                backgroundColor: '#f8fafc', padding: '12px 16px', borderRadius: '12px', border: '1px solid #e2e8f0', marginBottom: '24px'
              }}>
                <span style={{ fontWeight: 600, color: '#475569', fontSize: '14px' }}>启用该账号</span>
                <button
                  type="button"
                  className={`toggle-switch ${formData.is_active ? 'toggle-switch-on' : 'toggle-switch-off'}`}
                  onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
                >
                  <div className="toggle-knob" style={{ left: formData.is_active ? '25px' : '3px' }} />
                </button>
              </div>

              <div className="form-group">
                <label>平台类型</label>
                <select
                  className="form-control"
                  value={formData.platform}
                  onChange={(e) => handlePlatformChange(e.target.value as any)}
                  disabled={!!editingId}
                >
                  <option value="email">Email</option>
                  <option value="instagram">Instagram</option>
                  <option value="whatsapp">WhatsApp</option>
                </select>
              </div>

              {formData.platform === 'instagram' && !editingId && (
                <div style={{ background: '#eff6ff', border: '1px dashed #3b82f6', padding: '16px', borderRadius: '12px', marginBottom: '20px' }}>
                  <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} onClick={simulateMetaAuth}>
                    <ExternalLink size={16} /> 模拟 Meta 授权
                  </button>
                </div>
              )}

              <div className="form-group">
                <label>显示名称</label>
                <input
                  type="text" className="form-control"
                  value={formData.username}
                  onChange={e => setFormData({...formData, username: e.target.value})}
                />
              </div>

              {(formData.platform === 'instagram' || formData.platform === 'whatsapp') && (
                <div className="form-group">
                  <label>平台 ID (Platform ID)</label>
                  <input
                    type="text" className="form-control"
                    value={formData.platform_account_id}
                    onChange={e => setFormData({...formData, platform_account_id: e.target.value})}
                    disabled={!!editingId}
                  />
                </div>
              )}

              {formData.platform === 'email' ? (
                <>
                  <div className="form-group">
                    <label>授权码 / 密码</label>
                    <input
                      type="password" className="form-control"
                      value={formData.password}
                      onChange={e => setFormData({...formData, password: e.target.value})}
                    />
                  </div>
                  <div className="form-group">
                    <label>IMAP Host</label>
                    <input
                      type="text" className="form-control"
                      value={formData.config.host || ''}
                      onChange={e => setFormData({...formData, config: { ...formData.config, host: e.target.value }})}
                    />
                  </div>
                </>
              ) : (
                <div className="form-group">
                  <label>Access Token</label>
                  <input
                    type="password" className="form-control"
                    value={formData.config.access_token || formData.config.api_key || ''}
                    onChange={e => {
                      const key = formData.platform === 'instagram' ? 'access_token' : 'api_key';
                      setFormData({...formData, config: { ...formData.config, [key]: e.target.value }});
                    }}
                  />
                </div>
              )}

              <div className="modal-actions" style={{ display: 'flex', gap: '12px', marginTop: '32px', justifyContent: editingId ? 'space-between' : 'flex-end' }}>
                {editingId && (
                  <button className="btn btn-danger" onClick={() => setDeleteConfirmId(editingId)}>
                    <Trash2 size={16} />
                  </button>
                )}
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>取消</button>
                  <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                    {isSaving ? <Loader2 className="animate-spin" size={16} /> : '保存'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {deleteConfirmId && (
          <div className="modal-overlay" style={{ zIndex: 200 }}>
            <div className="modal-content" style={{ maxWidth: '360px', textAlign: 'center' }}>
              <AlertCircle size={40} color="#ef4444" style={{ marginBottom: '16px' }} />
              <h2 style={{ fontSize: '20px', marginBottom: '12px' }}>确认删除？</h2>
              <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '24px' }}>删除后无法恢复，且将尝试撤销第三方授权。</p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn btn-secondary" style={{ flex: 1, justifyContent: 'center' }} onClick={() => setDeleteConfirmId(null)}>取消</button>
                <button className="btn btn-primary" style={{ flex: 1, justifyContent: 'center', background: '#ef4444' }} onClick={confirmDelete}>确认</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default AccountSettingPage;