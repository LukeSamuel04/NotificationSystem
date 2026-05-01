// src/pages/AccountSettingPage.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/http';
import { Plus, Mail, Camera, MessageSquare, Trash2, Power, Settings, Loader2, AlertCircle } from 'lucide-react';
import type { AccountResponse } from '../types/account';

const AccountSettingPage: React.FC = () => {
  // 💥 改动1：剔除 LocalAccount，直接使用后端的 AccountResponse
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const defaultForm = { platform: 'email' as const, username: '', password: '', is_active: true, config: { host: '' } };
  const [formData, setFormData] = useState<any>(defaultForm);

  // 💥 改动2：纯粹的数据拉取，不再强行注入验证状态
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
      username: account.username,
      password: (account.config as any)?.password || '',
      is_active: account.is_active,
      config: account.config
    });
    setErrorMsg(null);
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setErrorMsg(null);
    try {
      if (editingId) {
        await apiClient.put(`/api/accounts/${editingId}`, formData);
      } else {
        await apiClient.post('/api/accounts', formData);
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
      await apiClient.delete(`/api/accounts/${deleteConfirmId}`);
      setDeleteConfirmId(null);
      setIsModalOpen(false);
      fetchAccounts();
    } catch (err) {
      alert("删除失败！");
    }
  };

  const handlePlatformChange = (platform: 'email' | 'instagram' | 'whatsapp') => {
    if (platform === 'email') {
      setFormData({ ...formData, platform, config: { host: '' } });
    } else if (platform === 'instagram') {
      setFormData({ ...formData, platform, config: { proxy_url: '' } });
    } else {
      setFormData({ ...formData, platform, config: { api_key: '' } });
    }
  };

  return (
    <>
      <style>{`
        .account-page { min-height: 100vh; background-color: #f8fafc; padding: 40px 32px; font-family: system-ui, -apple-system, sans-serif; }
        .account-container { max-width: 1000px; margin: 0 auto; }
        .account-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .account-header h1 { font-size: 28px; color: #0f172a; margin: 0 0 8px 0; }
        .account-header p { color: #64748b; margin: 0; font-size: 15px; }
        .btn { display: flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; }
        .btn-primary { background-color: #4f46e5; color: white; }
        .btn-primary:hover:not(:disabled) { background-color: #4338ca; }
        .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; }
        .btn-secondary { background-color: white; border: 1px solid #e2e8f0; color: #475569; }
        .btn-secondary:hover { background-color: #f8fafc; }
        .btn-danger { background-color: #fef2f2; color: #ef4444; border: 1px solid #fecaca; }
        .btn-danger:hover { background-color: #fee2e2; }
        .btn-danger-solid { background-color: #ef4444; color: white; }
        .btn-danger-solid:hover { background-color: #dc2626; }
        .account-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 24px; }
        .account-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); transition: box-shadow 0.2s; }
        .account-card:hover { box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
        .platform-icon { padding: 10px; border-radius: 8px; background-color: #f1f5f9; display: flex; align-items: center; justify-content: center; }
        
        .status-badge { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 99px; }
        .status-active { background-color: #dcfce7; color: #15803d; }
        .status-inactive { background-color: #f1f5f9; color: #475569; }
        .status-error { background-color: #fef2f2; color: #b91c1c; }

        .account-username { margin: 0 0 4px 0; font-size: 18px; color: #1e293b; word-break: break-all; }
        .account-platform { margin: 0 0 20px 0; font-size: 14px; color: #94a3b8; text-transform: capitalize; }
        .card-actions { display: flex; justify-content: flex-end; border-top: 1px solid #f1f5f9; padding-top: 16px; }
        .action-btn { background: none; border: none; color: #94a3b8; cursor: pointer; transition: color 0.2s; display: flex; align-items: center; justify-content: center; padding: 4px; }
        .action-btn:hover { color: #4f46e5; }
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(0, 0, 0, 0.5); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 50; }
        .modal-content { background: white; border-radius: 16px; padding: 32px; width: 100%; max-width: 460px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
        .modal-content h2 { margin: 0 0 24px 0; color: #0f172a; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; font-size: 14px; font-weight: 500; color: #334155; margin-bottom: 8px; }
        .form-control { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; outline: none; box-sizing: border-box; transition: border-color 0.2s; }
        .form-control:focus { border-color: #4f46e5; }
        .form-control:disabled { background-color: #f1f5f9; color: #94a3b8; cursor: not-allowed; }
        .modal-actions { display: flex; gap: 12px; margin-top: 32px; justify-content: flex-end; }
        .error-banner { background-color: #fef2f2; color: #b91c1c; padding: 12px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; display: flex; align-items: flex-start; gap: 8px; border: 1px solid #fecaca; }
        .loader-container { display: flex; justify-content: center; padding: 80px 0; }
        
        .toggle-switch { width: 44px; height: 24px; border-radius: 99px; position: relative; cursor: pointer; transition: background-color 0.2s; border: none; }
        .toggle-switch-on { background-color: #10b981; }
        .toggle-switch-off { background-color: #cbd5e1; }
        .toggle-knob { width: 18px; height: 18px; background-color: white; border-radius: 50%; position: absolute; top: 3px; transition: left 0.2s; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
      `}</style>

      <div className="account-page">
        <div className="account-container">
          <header className="account-header">
            <div>
              <h1>账号集成</h1>
              <p>管理您的消息来源，接入 AI 分析引擎</p>
            </div>
            <button className="btn btn-primary" onClick={handleOpenAdd}>
              <Plus size={20} /> 添加新账号
            </button>
          </header>

          {loading ? (
            <div className="loader-container">
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

                    {/* 💥 改动3：完全依赖后端的 is_active 和 is_valid 渲染状态 */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {!account.is_active ? (
                        <div className="status-badge status-inactive">
                          <Power size={12} /> 已禁用
                        </div>
                      ) : account.is_valid ? (
                        <div className="status-badge status-active">
                          <Power size={12} /> 已启用
                        </div>
                      ) : (
                        <div className="status-badge status-error">
                          <AlertCircle size={12} /> 已失效
                        </div>
                      )}
                    </div>

                  </div>

                  <h3 className="account-username">{account.username}</h3>
                  <p className="account-platform">{account.platform}</p>

                  <div className="card-actions">
                    <button className="action-btn" onClick={() => handleOpenEdit(account)}>
                      <Settings size={20} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {isModalOpen && (
          <div className="modal-overlay">
            <div className="modal-content">
              <h2>{editingId ? '账号配置' : '连接新平台'}</h2>

              {errorMsg && (
                <div className="error-banner">
                  <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <div className="form-group" style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                backgroundColor: '#f8fafc', padding: '12px 16px', borderRadius: '8px', border: '1px solid #e2e8f0'
              }}>
                <div>
                  <span style={{ display: 'block', fontWeight: 600, color: '#334155', fontSize: '14px' }}>账号状态</span>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>
                    {formData.is_active ? '已开启自动巡检与数据抓取' : '已暂停该账号的所有后台动作'}
                  </span>
                </div>
                <button
                  type="button"
                  className={`toggle-switch ${formData.is_active ? 'toggle-switch-on' : 'toggle-switch-off'}`}
                  onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
                  disabled={isSaving}
                >
                  <div className="toggle-knob" style={{ left: formData.is_active ? '23px' : '3px' }} />
                </button>
              </div>

              <div className="form-group">
                <label>选择平台</label>
                <select
                  className="form-control"
                  value={formData.platform}
                  onChange={(e) => handlePlatformChange(e.target.value as any)}
                  disabled={!!editingId}
                >
                  <option value="email">Email (IMAP)</option>
                  <option value="instagram">Instagram</option>
                  <option value="whatsapp">WhatsApp</option>
                </select>
              </div>

              <div className="form-group">
                <label>用户名 / 账号</label>
                <input
                  type="text" className="form-control"
                  value={formData.username}
                  onChange={e => setFormData({...formData, username: e.target.value})}
                />
              </div>

              <div className="form-group">
                <label>密码 / 授权码</label>
                <input
                  type="password" className="form-control" placeholder="输入密码或应用授权码"
                  value={formData.password}
                  onChange={e => setFormData({...formData, password: e.target.value})}
                />
              </div>

              {formData.platform === 'email' && (
                <div className="form-group">
                  <label>IMAP 服务器地址 (Host)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="如: imap.qq.com"
                    value={formData.config.host}
                    onChange={e => setFormData({...formData, config: { ...formData.config, host: e.target.value }})}
                    disabled={!!editingId} // 💥 改动4：处于编辑状态时，禁用 host 修改
                  />
                </div>
              )}

              {formData.platform === 'instagram' && (
                <div className="form-group">
                  <label>Proxy URL (代理地址)</label>
                  <input
                    type="text" className="form-control" placeholder="如: http://127.0.0.1:7890"
                    value={formData.config.proxy_url || ''}
                    onChange={e => setFormData({...formData, config: { ...formData.config, proxy_url: e.target.value }})}
                  />
                </div>
              )}

              {formData.platform === 'whatsapp' && (
                <div className="form-group">
                  <label>API Key / Token</label>
                  <input
                    type="text" className="form-control" placeholder="输入 WhatsApp API 令牌"
                    value={formData.config.api_key || ''}
                    onChange={e => setFormData({...formData, config: { ...formData.config, api_key: e.target.value }})}
                  />
                </div>
              )}

              <div className="modal-actions" style={{ justifyContent: editingId ? 'space-between' : 'flex-end' }}>
                {editingId && (
                  <button
                    className="btn btn-danger"
                    onClick={() => setDeleteConfirmId(editingId)}
                    disabled={isSaving}
                  >
                    <Trash2 size={16} /> 删除账号
                  </button>
                )}

                <div style={{ display: 'flex', gap: '12px' }}>
                  <button className="btn btn-secondary" onClick={() => setIsModalOpen(false)} disabled={isSaving}>
                    取消
                  </button>
                  <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                    {isSaving ? (
                      <><Loader2 size={16} className="animate-spin" /> 保存中...</>
                    ) : (
                      // 💥 改动5：如果是关掉激活，文案直接显示“保存配置”，不再让人觉得在做验证
                      formData.is_active ? '保存并启用' : '保存配置'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {deleteConfirmId && (
          <div className="modal-overlay" style={{ zIndex: 60 }}>
            <div className="modal-content" style={{ maxWidth: '360px', textAlign: 'center' }}>
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px', color: '#ef4444' }}>
                <AlertCircle size={48} />
              </div>
              <h2 style={{ fontSize: '20px', marginBottom: '12px' }}>确认删除此账号？</h2>
              <p style={{ color: '#64748b', fontSize: '14px', margin: '0 0 24px 0' }}>
                删除后，系统将彻底遗忘该账号。此操作无法撤销。
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="btn btn-secondary" style={{ flex: 1, justifyContent: 'center' }} onClick={() => setDeleteConfirmId(null)}>
                  取消
                </button>
                <button className="btn btn-danger-solid" style={{ flex: 1, justifyContent: 'center' }} onClick={confirmDelete}>
                  确认删除
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default AccountSettingPage;