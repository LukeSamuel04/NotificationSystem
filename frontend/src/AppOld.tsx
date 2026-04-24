import { useState, useEffect } from 'react'; // 修复警告1：移除了未使用的 React 导入
import './App.css';
import Button from './components/Button';
import Input from './components/Input';
import { Send, Layout, Mail, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { notificationApi } from './services/api';

// 定义通知数据的类型，确保与后端对齐
interface NotificationData {
  id: number;
  sender: string;
  subject: string;
  raw_content: string;
  priority_score: number;
  category: string;
}

function App() {
  const [sender, setSender] = useState('');
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [history, setHistory] = useState<NotificationData[]>([]);
  const [loading, setLoading] = useState(false);

  // --- 数据预清洗逻辑 ---
  const cleanData = (text: string) => {
    return text
      .trim()
      .replace(/[\x00-\x1F\x7F-\x9F]/g, "")
      .replace(/\\/g, "\\\\")
      .replace(/"/g, '\"');
  };

  // --- 获取数据方法 (拉取未完成的任务) ---
  const fetchHistory = async () => {
    try {
      const res = await notificationApi.getNotifications();
      setHistory(res.data);
    } catch (err) {
      console.error("Fail to get the data:", err);
    }
  };

  useEffect(() => {
    fetchHistory().catch(console.error); // 修复警告2：处理了未捕获的 Promise
  }, []);

  // --- 【新增】点击完成任务的核心逻辑 ---
  const handleMarkAsDone = async (id: number) => {
    try {
      // 1. 调用 api.ts 里的方法，通知后端将状态改为 done
      await notificationApi.markAsDone(id);

      // 2. 状态扭转成功后，重新拉取列表
      // 因为后端会自动过滤掉 done 的数据，所以这个任务会在前端瞬间消失
      fetchHistory().catch(console.error);
    } catch (err) {
      console.error("Failed to mark as done:", err);
      alert("Failed to update status!");
    }
  };

  // --- 提交并分析 ---
  const handleAnalyze = async () => {
    if (!content.trim()) {
      alert("Cannot submit blank content!");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        sender: cleanData(sender) || "Manual Input",
        subject: cleanData(subject) || "No Subject",
        raw_content: cleanData(content)
      };

      await notificationApi.collect(payload);

      setSubject('');
      setContent('');
      await fetchHistory();
    } catch (err: any) {
      console.error("API Error:", err.response?.data);
      alert("Submit failed, please check the server!");
    } finally {
      setLoading(false);
    }
  };

  // 根据分数获取颜色
  const getPriorityStyle = (score: number) => {
    if (score >= 8) return { color: '#ef4444', label: 'Urgent', bg: '#fef2f2' };
    if (score >= 5) return { color: '#f59e0b', label: 'Normal', bg: '#fffbeb' };
    return { color: '#10b981', label: 'Lower', bg: '#ecfdf5' };
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <Layout color="white" size={28} />
      </aside>

      <main className="main-content">
        {/* 左侧录入面板 */}
        <section className="panel-card" style={{ width: '400px' }}>
          <h2 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Mail size={24} /> Manual Email Input
          </h2>
          <Input label="Sender" value={sender} onChange={setSender} placeholder="e.g. Amazon.se" />
          <Input label="Subject" value={subject} onChange={setSubject} placeholder="Subject of the email" />
          <Input
            label="content"
            value={content}
            onChange={setContent}
            placeholder="Please paste content here..."
            isTextArea
            rows={12}
          />
          <Button
            label={loading ? "Analysing..." : "Send input request"}
            icon={<Send size={18} />}
            onClick={handleAnalyze}
          />
        </section>

        {/* 右侧展示面板 */}
        <section className="panel-card" style={{ flex: 1, overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 style={{ margin: 0 }}>Information to be solved</h2>
            <span style={{ fontSize: '14px', color: '#64748b' }}>All {history.length} records</span>
          </div>

          <div className="result-list" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {history.length === 0 ? (
              <div style={{ textAlign: 'center', marginTop: '50px', color: '#94a3b8' }}>
                <AlertTriangle size={48} style={{ marginBottom: '10px', opacity: 0.5 }} />
                <p>No data now, please enter the first email on the left!</p>
              </div>
            ) : (
              history.map((item) => {
                const style = getPriorityStyle(item.priority_score);
                return (
                  <div key={item.id} className="result-item" style={{
                    padding: '20px',
                    borderRadius: '12px',
                    backgroundColor: style.bg,
                    borderLeft: `6px solid ${style.color}`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'start',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '5px' }}>
                        <span style={{ fontWeight: 'bold', fontSize: '16px', color: '#1e293b' }}>{item.subject}</span>
                        <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '4px', backgroundColor: 'white', color: style.color, border: `1px solid ${style.color}` }}>
                          {style.label} {item.priority_score.toFixed(1)}
                        </span>
                      </div>
                      <div style={{ fontSize: '13px', color: '#64748b', marginBottom: '8px' }}>From: {item.sender} | Category: {item.category}</div>
                      <p style={{ margin: 0, fontSize: '14px', color: '#475569', lineHeight: 1.5 }}>
                        {item.raw_content.length > 120 ? item.raw_content.substring(0, 120) + "..." : item.raw_content}
                      </p>
                    </div>
                    {/* 【核心修改】：绑定 onClick 事件，点击触发销毁逻辑 */}
                    <div onClick={() => handleMarkAsDone(item.id)} title="Mark as done">
                      <CheckCircle2
                        size={24}
                        color="#cbd5e1"
                        style={{ marginLeft: '15px', cursor: 'pointer', transition: 'color 0.2s' }}
                        onMouseOver={(e) => e.currentTarget.style.color = '#10b981'} // 悬停变绿反馈
                        onMouseOut={(e) => e.currentTarget.style.color = '#cbd5e1'}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;