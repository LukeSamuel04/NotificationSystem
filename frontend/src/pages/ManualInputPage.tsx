import { useState } from 'react';
// 引入 lucide-react 图标库，用来美化界面
import { Send, Mail, CheckCircle2, User, FileText, Tag, Activity, Clock } from 'lucide-react';
// 引入你封装好的前后端通信 API
import { notificationApi } from '../services/api';
// 引入通用的 UI 组件
import Button from '../components/Button';
import Input from '../components/Input';

// ================= 类型定义 (TypeScript) =================
// 这里的接口严格对应后端的 Pydantic Schema (Email 返回体)
// 保证前端在使用数据时有代码提示，且不会取错字段名
interface NotificationData {
  id: number;
  sender: string;
  subject: string;
  raw_content: string;
  priority_score: number;
  category: string;
  received_at?: string; // 可选字段，兼容旧数据或未填写时间的场景
}

export default function ManualInputPage() {
  // ================= 1. 状态管理 (State Management) =================
  // 控制左侧表单输入框的状态
  const [sender, setSender] = useState('');
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [receivedTime, setReceivedTime] = useState('');

  // 控制右侧分析结果的状态
  // 初始值为 null，表示还没开始分析；分析成功后存入后端的完整对象
  const [analyzedResult, setAnalyzedResult] = useState<NotificationData | null>(null);

  // 控制按钮的“加载中”状态，防止用户连续猛点多次发起重复请求
  const [loading, setLoading] = useState(false);

  // ================= 2. 数据清洗层 (Data Cleansing) =================
  // 核心逻辑：防止用户复制粘贴的奇葩文本导致后端的 JSON 解析崩溃
  const cleanData = (text: string) => {
    return text
      .trim() // 去除首尾的多余空格
      .replace(/[\x00-\x1F\x7F-\x9F]/g, "") // 抹除不可见的控制字符（如某些隐形的换行符或乱码）
      .replace(/\\/g, "\\\\") // 转义反斜杠
      .replace(/"/g, '\"'); // 转义双引号
  };

  // ================= 3. 核心交互层 (API Call & Event Handling) =================
  const handleAnalyze = async () => {
    // 拦截：如果正文是空的，直接弹窗阻止，不浪费服务器算力
    if (!content.trim()) {
      alert("Cannot submit blank content!");
      return;
    }

    // 扭转状态：按钮变成加载中，并清空右侧上一次的分析结果
    setLoading(true);
    setAnalyzedResult(null);

    try {
      // 组装 Payload：将前端的 state 打包成后端需要的 JSON 格式
      // 注意：这里的键名 (sender, subject...) 必须和后端 EmailCreate 完全一致
      const payload: any = {
        sender: cleanData(sender) || "Manual Input",
        subject: cleanData(subject) || "No Subject",
        raw_content: cleanData(content),
      };

      // 动态挂载：只有用户在日历控件选了时间，才把 received_at 传给后端
      if (receivedTime) {
        // 将本地时间转换为标准的 ISO 格式 (例如: 2026-04-22T20:22:21.000Z)
        payload.received_at = new Date(receivedTime).toISOString();
      }

      // 异步调用：向 FastAPI 发送 POST 请求，并等待处理完毕
      const res = await notificationApi.collect(payload);

      // 渲染触发：拿到带分数的返回数据存入 State，React 会自动刷新右侧组件把结果画出来
      setAnalyzedResult(res.data);

    } catch (err: any) {
      console.error("API Error:", err);
      // 精准排错：捕获 422 错误，提示是否是前后端字段对不上
      if (err.response?.status === 422) {
         alert("Data validation failed! Does your backend EmailCreate schema include 'received_at'?");
      } else {
         alert("Submit failed, please check the server console!");
      }
    } finally {
      // 无论成功还是失败，最后都必须解除加载状态，释放按钮
      setLoading(false);
    }
  };

  // ================= 4. 样式辅助函数 (UI Helpers) =================
  // 根据不同的优先级分数，返回对应的文字颜色、背景色和标签文字
  const getPriorityStyle = (score: number) => {
    if (score >= 8) return { color: '#ef4444', label: 'Urgent', bg: '#fef2f2' };
    if (score >= 5) return { color: '#f59e0b', label: 'Normal', bg: '#fffbeb' };
    return { color: '#10b981', label: 'Lower', bg: '#ecfdf5' };
  };

  // ================= 5. 视图渲染 (JSX) =================
  return (
    <div style={{ display: 'flex', gap: '20px', height: '100%', padding: '20px' }}>

      {/* ---------------- 左侧：表单录入区 ---------------- */}
      <section className="panel-card" style={{ width: '450px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <h2 style={{ marginTop: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Mail size={24} /> Manual Email Input
        </h2>

        {/* 调用你封装好的 Input 组件，双向绑定对应的 state */}
        <Input label="Sender" value={sender} onChange={setSender} placeholder="e.g. manager@company.com" />
        <Input label="Subject" value={subject} onChange={setSubject} placeholder="Enter the subject..." />

        {/* HTML 原生的日期时间选择器 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <label style={{ fontSize: '14px', fontWeight: 600, color: '#475569' }}>Received Time</label>
          <input
            type="datetime-local"
            value={receivedTime}
            onChange={(e) => setReceivedTime(e.target.value)}
            style={{ padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', outline: 'none', fontFamily: 'inherit' }}
          />
        </div>

        {/* 文本域控件 (TextArea)，允许输入多行长文本 */}
        <Input
          label="Email Content"
          value={content}
          onChange={setContent}
          placeholder="Please paste the exact email content here..."
          isTextArea
          rows={8}
        />

        <div style={{ marginTop: 'auto' }}>
          {/* 提交按钮：绑定了点击事件，并根据 loading 状态动态改变文字 */}
          <Button
            label={loading ? "AI is Analyzing..." : "Submit for Analysis and Input"}
            icon={<Send size={18} />}
            onClick={handleAnalyze}
          />
        </div>
      </section>

      {/* ---------------- 右侧：AI 诊断结果区 ---------------- */}
      <section className="panel-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <h2 style={{ marginTop: 0, marginBottom: '20px' }}>AI Diagnostic Result</h2>

        {/* 条件渲染：如果 analyzedResult 是 null，显示占位的提示信息 */}
        {!analyzedResult ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
            <Activity size={64} style={{ marginBottom: '15px', opacity: 0.2 }} />
            <p>Awaiting data submission...</p>
          </div>
        ) : (
          // 条件渲染：如果有数据，则渲染华丽的诊断卡片
          <div style={{
            padding: '25px', borderRadius: '12px',
            // 动态注入计算好的背景色和边框颜色
            backgroundColor: getPriorityStyle(analyzedResult.priority_score).bg,
            border: `1px solid ${getPriorityStyle(analyzedResult.priority_score).color}40`,
          }}>

            {/* 卡片头部：分数胶囊和分类标签 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', paddingBottom: '15px', borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
              <div style={{ display: 'flex', gap: '10px' }}>
                <span style={{ padding: '6px 12px', borderRadius: '6px', fontWeight: 'bold', backgroundColor: getPriorityStyle(analyzedResult.priority_score).color, color: 'white' }}>
                  {getPriorityStyle(analyzedResult.priority_score).label} ({analyzedResult.priority_score.toFixed(2)})
                </span>
                <span style={{ padding: '6px 12px', borderRadius: '6px', backgroundColor: 'white', color: '#475569', display: 'flex', alignItems: 'center', gap: '5px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                  <Tag size={14} /> {analyzedResult.category}
                </span>
              </div>
              <CheckCircle2 size={32} color={getPriorityStyle(analyzedResult.priority_score).color} />
            </div>

            {/* 卡片主体：展示详细属性 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              <div>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#1e293b', marginBottom: '4px' }}>
                  <FileText size={16} /> Subject
                </strong>
                <div style={{ fontSize: '18px', color: '#0f172a' }}>{analyzedResult.subject}</div>
              </div>

              <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap' }}>
                <div>
                  <strong style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#475569', marginBottom: '4px' }}>
                    <User size={16} /> Sender
                  </strong>
                  <div style={{ color: '#334155' }}>{analyzedResult.sender}</div>
                </div>

                {/* 逻辑判断：如果后端传回了接收时间，或者前端自己选了时间，才渲染这个区块 */}
                {(analyzedResult.received_at || receivedTime) && (
                  <div>
                    <strong style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#475569', marginBottom: '4px' }}>
                      <Clock size={16} /> Received Time
                    </strong>
                    <div style={{ color: '#334155' }}>
                      {/* 将 ISO 时间字符串格式化为人类可读的本地时间 */}
                      {analyzedResult.received_at ? new Date(analyzedResult.received_at).toLocaleString() : new Date(receivedTime).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              {/* 正文片段展示 */}
              <div style={{ marginTop: '10px' }}>
                <strong style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#475569', marginBottom: '8px' }}>
                  <Mail size={16} /> Raw Content
                </strong>
                <div style={{
                  backgroundColor: 'white', padding: '15px', borderRadius: '8px',
                  color: '#475569', lineHeight: 1.6, whiteSpace: 'pre-wrap', maxHeight: '400px', overflowY: 'auto',
                  border: '1px solid #e2e8f0'
                }}>
                  {analyzedResult.raw_content}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}