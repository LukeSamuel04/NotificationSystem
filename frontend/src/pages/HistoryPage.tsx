// src/pages/HistoryPage.tsx
import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { Archive, RotateCcw, User, Tag, ChevronDown, ChevronUp, Search, RefreshCw, Sparkles, CheckCircle, AlertTriangle } from 'lucide-react';
import { notificationApi } from '../api/notification';
import type { AppNotification } from '../types';

// 引入对齐 Dashboard 的纯文本提取函数
const parseHtmlToPlainText = (htmlString: string) => {
  if (!htmlString) return "";

  let html = htmlString.replace(/<(style|script|head)[^>]*>[\s\S]*?<\/\1>/gi, '');
  html = html.replace(/<\/?(div|p|br|tr|td|table|tbody|h[1-6]|li)[^>]*>/gi, '\n');

  const doc = new DOMParser().parseFromString(html, 'text/html');
  let text = doc.body.textContent || "";
  text = text.replace(/[\u00A0\u2007\u200B-\u200D\uFEFF\u2028\u2029]/g, ' ');

  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .join('\n\n');
};

const CATEGORIES = [
  { id: 'all', label: 'All History' },
  { id: 'urgent_alert', label: 'Urgent' },
  { id: 'study_work', label: 'Study/Work' },
  { id: 'bills_housing', label: 'Housing' },
  { id: 'social_personal', label: 'Social' },
  { id: 'advertisement_spam', label: 'Spam' },
];

export default function HistoryPage() {
  const [history, setHistory] = useState<AppNotification[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const location = useLocation();

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await notificationApi.getHistory();

      // 优先按照 updated_at (最近处理时间) 降序排列
      const sortedData = ((res as AppNotification[]) || []).sort((a, b) => {
        const timeA = a.updated_at ? new Date(a.updated_at).getTime() : 0;
        const timeB = b.updated_at ? new Date(b.updated_at).getTime() : 0;
        return timeB - timeA;
      });

      setHistory(sortedData);
    } catch (err) {
      console.error("Failed to fetch history:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [location.pathname]);

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

  const handleRestore = async (id: number) => {
    try {
      await notificationApi.restoreNotification(id);
      fetchHistory();
    } catch (err) {
      console.error("Failed to restore task:", err);
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

  return (
    <div style={{ height: '100%', overflowY: 'auto', overflowX: 'hidden', padding: '20px', boxSizing: 'border-box', backgroundColor: '#f8fafc', width: '100%' }}>
      <section className="panel-card" style={{ margin: 0, padding: '20px', minHeight: '100%', boxSizing: 'border-box', width: '100%' }}>

        {/* 顶部控制栏 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px', color: '#475569' }}>
            <Archive size={28} color="#64748b" /> Archived History
          </h2>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={fetchHistory}
              disabled={loading}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px',
                backgroundColor: '#f1f5f9', border: 'none', borderRadius: '6px',
                cursor: 'pointer', color: '#64748b', fontSize: '13px', fontWeight: 600
              }}
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Updating...' : 'Refresh'}
            </button>
            <span style={{ fontSize: '13px', color: '#64748b', backgroundColor: '#f1f5f9', padding: '4px 12px', borderRadius: '20px', fontWeight: 'bold' }}>
              {filteredData.length} Items
            </span>
          </div>
        </div>

        {/* 过滤与搜索 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginBottom: '25px', paddingBottom: '20px', borderBottom: '1px solid #f1f5f9' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={18} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              placeholder="Search archived messages..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%', padding: '10px 10px 10px 40px', borderRadius: '8px',
                border: '1px solid #e2e8f0', outline: 'none', fontSize: '14px',
                boxSizing: 'border-box', backgroundColor: '#ffffff'
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
                  backgroundColor: selectedCategory === cat.id ? '#64748b' : 'white',
                  color: selectedCategory === cat.id ? 'white' : '#64748b',
                  borderColor: selectedCategory === cat.id ? '#64748b' : '#e2e8f0'
                }}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* 历史卡片列表 或 空状态提示 */}
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            {filteredData.map((item) => {
              const isExpanded = expandedIds.has(item.id);

              // 💥 【替换点 2】：渲染的时候，读取 item.cleaned_content，并经过纯文本转换
              const textContent = parseHtmlToPlainText(item.cleaned_content || "");

              const isLongContent = textContent.length > 150 || (textContent.match(/\n/g) || []).length >= 3;

              return (
                <div key={item.id} style={{
                  padding: '20px', borderRadius: '12px', backgroundColor: '#ffffff',
                  borderLeft: `4px solid #cbd5e1`,
                  display: 'flex', flexDirection: 'column',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.05)', transition: 'all 0.2s',
                  width: '100%', boxSizing: 'border-box'
                }}>

                  {/* 标题区与撤销按钮 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px', gap: '15px' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{
                        fontWeight: 'bold', fontSize: '16px', color: '#475569',
                        display: 'block', marginBottom: '8px',
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        textDecoration: 'line-through', textDecorationColor: '#cbd5e1'
                      }} title={item.subject}>
                        {item.subject}
                      </span>
                      <div style={{ display: 'flex', flexWrap: 'nowrap', gap: '8px', opacity: 0.7 }}>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: '#f1f5f9', color: '#64748b', fontWeight: 'bold' }}>
                          Score: {item.priority_score != null ? item.priority_score.toFixed(1) : 'Pending'}
                        </span>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: '#f1f5f9', color: '#64748b', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Tag size={12} /> {item.category || 'Uncategorized'}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleRestore(item.id)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px',
                        backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px',
                        cursor: 'pointer', color: '#64748b', fontSize: '13px', fontWeight: 600,
                        transition: 'all 0.2s', flexShrink: 0
                      }}
                    >
                      <RotateCcw size={16} /> Undo
                    </button>
                  </div>

                  {/* AI Summary (灰色调) */}
                  {item.summary && (
                    <div style={{
                      backgroundColor: '#f8fafc', border: '1px solid #f1f5f9',
                      borderRadius: '8px', padding: '10px 12px', marginBottom: '12px',
                      display: 'flex', gap: '8px', alignItems: 'flex-start'
                    }}>
                      <Sparkles size={16} color="#94a3b8" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span style={{ fontSize: '13px', color: '#64748b', fontWeight: 500, lineHeight: 1.5 }}>
                        {item.summary}
                      </span>
                    </div>
                  )}

                  {/* 元数据区：发件人 与 处理时间 */}
                  <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '12px', display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><User size={14} /> {item.sender}</span>

                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#10b981' }}>
                      <CheckCircle size={14} /> Done at: {new Date(item.updated_at || item.created_at || '').toLocaleString()}
                    </span>
                  </div>

                  {/* 正文 */}
                  <div style={{
                    margin: 0, fontSize: '14px', color: '#64748b', lineHeight: 1.6,
                    display: isExpanded || !isLongContent ? 'block' : '-webkit-box',
                    WebkitLineClamp: isExpanded ? 'unset' : 2,
                    WebkitBoxOrient: 'vertical', overflow: 'hidden', whiteSpace: 'pre-wrap', wordBreak: 'break-word'
                  }}>
                    {textContent}
                  </div>

                  {isLongContent && (
                    <div
                      onClick={() => toggleExpand(item.id)}
                      style={{
                        marginTop: '10px', display: 'flex', alignItems: 'center', gap: '5px',
                        fontSize: '13px', color: '#94a3b8', cursor: 'pointer', fontWeight: 600
                      }}
                    >
                      {isExpanded ? <><ChevronUp size={16} /> Less</> : <><ChevronDown size={16} /> More</>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}