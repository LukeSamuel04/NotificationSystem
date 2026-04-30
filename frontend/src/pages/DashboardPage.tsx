// src/pages/DashboardPage.tsx
import { useState, useEffect, useMemo } from 'react';
import { AlertTriangle, CheckCircle2, Inbox, Clock, User, Tag, ChevronDown, ChevronUp, Search, Sparkles } from 'lucide-react';
import { notificationApi } from '../api/notification';
// 【核心修复】：使用 AppNotification 避开浏览器原生保留字
import type { AppNotification } from '../types';

// 💡 【小提示】：因为你的后端现在已经有了“大厂级”的 html_cleaner.py，
// 这里其实收到的已经是极度干净的 Markdown/纯文本了。
// 这个函数现在相当于只做个最终的保险（清理首尾空格和极端多余的换行），性能极其丝滑。
const parseHtmlToPlainText = (htmlString: string) => {
  if (!htmlString) return "";

  // 1. 物理铲除所有的 CSS、脚本和头部信息 (对现在的 cleaned_content 来说基本是空跑)
  let html = htmlString.replace(/<(style|script|head)[^>]*>[\s\S]*?<\/\1>/gi, '');

  // 2. 把所有负责排版的块级标签，一律打平成一个简单的换行符 \n
  html = html.replace(/<\/?(div|p|br|tr|td|table|tbody|h[1-6]|li)[^>]*>/gi, '\n');

  // 3. 让 DOMParser 仅仅负责解码
  const doc = new DOMParser().parseFromString(html, 'text/html');
  let text = doc.body.textContent || "";

  // 4. 把一切稀奇古怪的隐藏空白全部拍扁成普通空格
  text = text.replace(/[\u00A0\u2007\u200B-\u200D\uFEFF\u2028\u2029]/g, ' ');

  // 5. 💣 终极碎纸机：打散 -> 脱水 -> 过滤 -> 重组
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .join('\n\n');
};

// 硬编码分类列表
const CATEGORIES = [
  { id: 'all', label: 'All Tasks' },
  { id: 'urgent_alert', label: 'Urgent' },
  { id: 'study_work', label: 'Study/Work' },
  { id: 'bills_housing', label: 'Housing' },
  { id: 'social_personal', label: 'Social' },
  { id: 'advertisement_spam', label: 'Spam' },
];

export default function DashboardPage() {
  const [history, setHistory] = useState<AppNotification[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const fetchHistory = async () => {
    try {
      const res = await notificationApi.getNotifications();
      const sortedData = (res || []).sort((a: AppNotification, b: AppNotification) => {
        const scoreA = a.priority_score ?? -1;
        const scoreB = b.priority_score ?? -1;
        return scoreB - scoreA;
      });
      setHistory(sortedData);
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
    }
  };

  useEffect(() => {
    fetchHistory().catch(console.error);
  }, []);

  const filteredData = useMemo(() => {
    return history.filter(item => {
      // 💥 【替换点 1】：搜索的时候，读取 item.cleaned_content
      const textToSearch = `${item.subject} ${item.sender} ${item.cleaned_content}`.toLowerCase();
      const matchesSearch = textToSearch.includes(searchQuery.toLowerCase());

      const itemCategory = item.category || 'uncategorized';
      const matchesCategory = selectedCategory === 'all' || itemCategory === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [history, searchQuery, selectedCategory]);

  const handleMarkAsDone = async (id: number) => {
    try {
      await notificationApi.markAsDone(id);
      fetchHistory().catch(console.error);
    } catch (err) {
      console.error("Failed to mark as done:", err);
      alert("Failed to update status!");
    }
  };

  const toggleExpand = (id: number) => {
    setExpandedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) newSet.delete(id);
      else newSet.add(id);
      return newSet;
    });
  };

  const getPriorityStyle = (score?: number | null) => {
    if (score === null || score === undefined) return { color: '#94a3b8', label: 'AI Pending', bg: '#f8fafc' };
    if (score >= 8) return { color: '#ef4444', label: 'Urgent', bg: '#fef2f2' };
    if (score >= 5) return { color: '#f59e0b', label: 'Normal', bg: '#fffbeb' };
    return { color: '#10b981', label: 'Lower', bg: '#ecfdf5' };
  };

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '20px', boxSizing: 'border-box' }}>
      <section className="panel-card" style={{ margin: 0, padding: '20px' }}>

        {/* 顶部标题区 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px', color: '#0f172a' }}>
            <Inbox size={28} color="#3b82f6" /> Pending Tasks
          </h2>
          <span style={{ fontSize: '13px', color: '#64748b', backgroundColor: '#f1f5f9', padding: '4px 12px', borderRadius: '20px', fontWeight: 'bold' }}>
            Showing {filteredData.length} of {history.length}
          </span>
        </div>

        {/* 工具栏：搜索 + 分类过滤 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginBottom: '25px', paddingBottom: '20px', borderBottom: '1px solid #f1f5f9' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={18} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search by subject, sender or content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%', padding: '10px 10px 10px 40px', borderRadius: '8px',
                border: '1px solid #e2e8f0', outline: 'none', fontSize: '14px',
                boxSizing: 'border-box', backgroundColor: '#f8fafc'
              }}
            />
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {CATEGORIES.map(cat => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                style={{
                  padding: '6px 14px', borderRadius: '20px', fontSize: '13px', fontWeight: 600,
                  cursor: 'pointer', border: '1px solid', transition: 'all 0.2s',
                  backgroundColor: selectedCategory === cat.id ? '#3b82f6' : 'white',
                  color: selectedCategory === cat.id ? 'white' : '#64748b',
                  borderColor: selectedCategory === cat.id ? '#3b82f6' : '#e2e8f0'
                }}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* 任务列表区 */}
        {filteredData.length === 0 ? (
          <div style={{ textAlign: 'center', marginTop: '60px', color: '#94a3b8', paddingBottom: '60px' }}>
            <AlertTriangle size={48} style={{ marginBottom: '15px', opacity: 0.3, margin: '0 auto' }} />
            <h3 style={{ margin: '0 0 10px 0', color: '#64748b' }}>No matches found</h3>
            <p style={{ fontSize: '14px' }}>Try adjusting your search or filters.</p>
            <button
              onClick={() => {setSearchQuery(''); setSelectedCategory('all');}}
              style={{ marginTop: '15px', color: '#3b82f6', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
            >
              Reset all filters
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '20px', alignItems: 'flex-start' }}>
            {filteredData.map((item) => {
              const style = getPriorityStyle(item.priority_score);
              const isExpanded = expandedIds.has(item.id);

              // 💥 【替换点 2】：渲染的时候，读取 item.cleaned_content
              const textContent = parseHtmlToPlainText(item.cleaned_content || "");

              const isLongContent = textContent.length > 150 || (textContent.match(/\n/g) || []).length >= 3;

              return (
                <div key={item.id} style={{
                  padding: '20px', borderRadius: '12px', backgroundColor: style.bg,
                  borderTop: `6px solid ${style.color}`,
                  display: 'flex', flexDirection: 'column', height: 'max-content',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)', transition: 'all 0.2s',
                  wordBreak: 'break-word', overflowWrap: 'break-word'
                }}>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div style={{ flex: 1, paddingRight: '15px', overflow: 'hidden' }}>
                      <span style={{
                        fontWeight: 'bold', fontSize: '17px', color: '#1e293b',
                        display: 'block', marginBottom: '8px',
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                      }} title={item.subject}>
                        {item.subject}
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'nowrap', gap: '8px', overflow: 'hidden' }}>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: 'white', color: style.color, border: `1px solid ${style.color}`, fontWeight: 'bold', whiteSpace: 'nowrap' }}>
                          {style.label} {item.priority_score != null ? item.priority_score.toFixed(1) : ''}
                        </span>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: '#e2e8f0', color: '#475569', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
                          <Tag size={12} style={{ flexShrink: 0 }} /> {item.category || 'Uncategorized'}
                        </span>
                      </div>
                    </div>

                    <div onClick={() => handleMarkAsDone(item.id)} title="Mark as done">
                      <CheckCircle2
                        size={30} color="#cbd5e1"
                        style={{ cursor: 'pointer', transition: 'all 0.2s', marginTop: '2px', flexShrink: 0 }}
                        onMouseOver={(e) => { e.currentTarget.style.color = '#10b981'; e.currentTarget.style.transform = 'scale(1.1)'; }}
                        onMouseOut={(e) => { e.currentTarget.style.color = '#cbd5e1'; e.currentTarget.style.transform = 'scale(1)'; }}
                      />
                    </div>
                  </div>

                  {/* AI Summary 模块 */}
                  {item.summary && (
                    <div style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.6)', border: '1px solid #e2e8f0',
                      borderRadius: '8px', padding: '10px 12px', marginBottom: '12px',
                      display: 'flex', gap: '8px', alignItems: 'flex-start'
                    }}>
                      <Sparkles size={16} color="#8b5cf6" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span style={{ fontSize: '13px', color: '#4c1d95', fontWeight: 500, lineHeight: 1.5 }}>
                        {item.summary}
                      </span>
                    </div>
                  )}

                  <div style={{
                    fontSize: '13px', color: '#64748b', marginBottom: '12px', display: 'flex', gap: '15px',
                    backgroundColor: 'white', padding: '8px 12px', borderRadius: '6px'
                  }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      <User size={14} style={{ flexShrink: 0 }}/> {item.sender}
                    </span>
                    {item.received_at && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
                        <Clock size={14} /> {new Date(item.received_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  <div style={{
                    margin: 0, fontSize: '14px', color: '#475569', lineHeight: 1.6,
                    display: isExpanded || !isLongContent ? 'block' : '-webkit-box',
                    WebkitLineClamp: isExpanded ? 'unset' : 3,
                    WebkitBoxOrient: 'vertical', overflow: 'hidden', whiteSpace: 'pre-wrap',
                    height: isExpanded || !isLongContent ? 'auto' : '4.8em'
                  }}>
                    {textContent}
                  </div>

                  {isLongContent && (
                    <div
                      onClick={() => toggleExpand(item.id)}
                      style={{
                        marginTop: '15px', paddingTop: '10px', borderTop: '1px dashed #cbd5e1',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
                        fontSize: '13px', color: '#3b82f6', cursor: 'pointer', fontWeight: 600
                      }}
                    >
                      {isExpanded ? <><ChevronUp size={16} /> Show Less</> : <><ChevronDown size={16} /> Read More</>}
                    </div>
                  )}

                </div>
              );
            })
          }
          </div>
        )}
      </section>
    </div>
  );
}