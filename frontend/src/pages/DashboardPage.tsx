import { useState, useEffect, useMemo } from 'react';
import { AlertTriangle, CheckCircle2, Inbox, Clock, User, Tag, ChevronDown, ChevronUp, Search} from 'lucide-react';
import { notificationApi } from '../services/api';

interface NotificationData {
  id: number;
  sender: string;
  subject: string;
  raw_content: string;
  priority_score: number;
  category: string;
  received_at?: string;
}

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
  const [history, setHistory] = useState<NotificationData[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  // 【新增状态】：搜索词和选中的分类
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const fetchHistory = async () => {
    try {
      const res = await notificationApi.getNotifications();
      // 保持优先级排序逻辑
      const sortedData = (res.data || []).sort((a: NotificationData, b: NotificationData) => b.priority_score - a.priority_score);
      setHistory(sortedData);
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
    }
  };

  useEffect(() => {
    fetchHistory().catch(console.error);
  }, []);

  // 【核心逻辑】：前端过滤算法
  // 使用 useMemo 确保只有当 history/search/category 变化时才重新计算，优化性能
  const filteredData = useMemo(() => {
    return history.filter(item => {
      const matchesSearch =
        item.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.sender.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.raw_content.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory;

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

  const getPriorityStyle = (score: number) => {
    if (score >= 8) return { color: '#ef4444', label: 'Urgent', bg: '#fef2f2' };
    if (score >= 5) return { color: '#f59e0b', label: 'Normal', bg: '#fffbeb' };
    return { color: '#10b981', label: 'Lower', bg: '#ecfdf5' };
  };

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '20px', boxSizing: 'border-box' }}>

      <section className="panel-card" style={{ margin: 0, padding: '20px' }}>

        {/* 1. 顶部标题区 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px', color: '#0f172a' }}>
            <Inbox size={28} color="#3b82f6" /> Pending Tasks
          </h2>
          <span style={{ fontSize: '13px', color: '#64748b', backgroundColor: '#f1f5f9', padding: '4px 12px', borderRadius: '20px', fontWeight: 'bold' }}>
            Showing {filteredData.length} of {history.length}
          </span>
        </div>

        {/* 2. 【新增】工具栏：搜索 + 分类过滤 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginBottom: '25px', paddingBottom: '20px', borderBottom: '1px solid #f1f5f9' }}>

          {/* 搜索框 */}
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

          {/* 分类切换按钮 (Pills) */}
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

        {/* 3. 任务列表区 */}
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
              const rawText = item.raw_content || "";
              const isLongContent = rawText.length > 150 || (rawText.match(/\n/g) || []).length >= 3;

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
                          {style.label} {item.priority_score.toFixed(1)}
                        </span>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', backgroundColor: '#e2e8f0', color: '#475569', display: 'flex', alignItems: 'center', gap: '4px', whiteSpace: 'nowrap' }}>
                          <Tag size={12} style={{ flexShrink: 0 }} /> {item.category}
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
                    {rawText}
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