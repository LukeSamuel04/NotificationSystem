import { useState, useEffect } from "react";
import { formatDistanceToNow } from "date-fns";
import { zhCN } from "date-fns/locale";
import {
  Mail,
  Camera,
  Archive,
  ThumbsUp,
  ThumbsDown,
  Zap,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  MessageCircle,
  Sparkles,
  Tag
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { notificationApi } from "@/api/notification";
import type { GroupedNotification } from "@/types/notification";

interface NotificationCardProps {
  group: GroupedNotification;
  onUpdate: () => void;
}

const CATEGORY_MAP: Record<number, string> = {
  1: "紧急告警",
  2: "验证码与重置",
  3: "工作与学业",
  4: "财务与物流",
  5: "私人社交",
  6: "系统与订阅",
  7: "垃圾与推销"
};

export function NotificationCard({ group, onUpdate }: NotificationCardProps) {
  const [isArchiving, setIsArchiving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const [localIsRead, setLocalIsRead] = useState(group.is_read);

  useEffect(() => {
    setLocalIsRead(group.is_read);
  }, [group.is_read]);

  const latestMessage = group.messages[group.messages.length - 1];
  const [localFeedback, setLocalFeedback] = useState<number | null>(
    latestMessage?.analysis_payload?.user_feedback_score || null
  );

  const isEmail = group.platform === "email";
  const receivedTime = group.latest_received_at
    ? formatDistanceToNow(new Date(group.latest_received_at), { addSuffix: true, locale: zhCN })
    : "剛剛";

  // 精准对接真实的 im_session_state、current_topic 和 summary_snapshot
  const imSummary = latestMessage?.im_session_state?.current_topic || latestMessage?.im_session_state?.summary_snapshot;

  const contentPreview = isEmail
    ? (latestMessage?.email_analysis?.summary || latestMessage?.cleaned_content || "暫無內容...")
    : (imSummary || latestMessage?.cleaned_content || "暫無內容...");

  const displayTitle = !isEmail && imSummary ? imSummary : group.title;

  // 映射 AI 分类
  const categoryId = latestMessage?.email_analysis?.category_id;
  const categoryName = latestMessage?.email_analysis?.category;
  const mappedCategory = categoryId ? CATEGORY_MAP[categoryId] : null;
  const displayCategory = categoryName || mappedCategory || (categoryId ? `類別 ${categoryId}` : null);

  const isArchived = latestMessage?.status === "archived";

  // 保持你设定的 1-10 分变色梯队
  const getScoreVisuals = (score: number) => {
    if (score >= 8) return {
      badgeColor: "bg-red-100 text-red-800 border-red-200",
      icon: <Zap className="w-3 h-3 text-red-600 fill-red-600" />,
      cardBg: "bg-red-50/30 hover:bg-red-50/60 border-red-100"
    };
    if (score >= 5) return {
      badgeColor: "bg-orange-100 text-orange-800 border-orange-200",
      icon: <Zap className="w-3 h-3 text-orange-500" />,
      cardBg: "bg-orange-50/30 hover:bg-orange-50/60 border-orange-100"
    };
    return {
      badgeColor: "bg-green-100 text-green-800 border-green-200",
      icon: null,
      cardBg: "bg-green-50/30 hover:bg-green-50/60 border-green-100"
    };
  };
  const scoreVisual = getScoreVisuals(group.priority_score);

  const handleArchive = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsArchiving(true);
    const targetStatus = isArchived ? "processed" : "archived";
    try {
      await Promise.all(
        group.messages.map(msg => notificationApi.updateNotification(msg.id, { status: targetStatus }))
      );
      onUpdate();
    } catch (error) {
      console.error(isArchived ? "取消归档失败" : "批量归档失败", error);
      setIsArchiving(false);
    }
  };

  // 🎯 新增功能：将整组会话消息一键“标记为未读”
  const handleMarkUnread = async (e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止卡片展开/折叠
    try {
      await Promise.all(
        group.messages.map(msg => notificationApi.updateNotification(msg.id, { is_read: false }))
      );
      setLocalIsRead(false);
      group.is_read = false;
      onUpdate(); // 通知主看板同步刷新状态
    } catch (error) {
      console.error("标记未读失败", error);
    }
  };

  const handleFeedback = async (e: React.MouseEvent, score: number) => {
    e.stopPropagation();
    if (localFeedback === score || !latestMessage) return;
    setIsSubmitting(true);
    try {
      await notificationApi.submitFeedback(latestMessage.id, score);
      setLocalFeedback(score);
    } catch (error) {
      console.error("反饋提交失敗", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExpand = () => {
    setIsExpanded(!isExpanded);
    if (!isExpanded && !localIsRead) {
      group.messages.filter(m => !m.is_read).forEach(m => {
        notificationApi.updateNotification(m.id, { is_read: true }).catch(()=>{});
      });
      setLocalIsRead(true);
      group.is_read = true;
    }
  };

  return (
    <Card
      onClick={handleExpand}
      className={`group relative overflow-hidden transition-all duration-300 border cursor-pointer
        ${scoreVisual.cardBg}
        ${isExpanded ? 'shadow-md ring-1 ring-slate-200' : 'hover:shadow-sm'} 
        ${isArchiving ? 'opacity-50 scale-[0.98] pointer-events-none' : ''}
      `}
    >
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${group.priority_score >= 8 ? 'bg-red-500' : group.priority_score >= 5 ? 'bg-orange-400' : 'bg-green-400'}`} />

      <CardContent className="p-5 pl-6 flex flex-col gap-4">
        <div className="flex gap-4">
          <div className="shrink-0 pt-1">
            {isEmail ? (
              <div className="p-2.5 bg-blue-50/80 text-blue-600 rounded-xl shadow-sm border border-blue-100">
                <Mail className="h-5 w-5" />
              </div>
            ) : (
              <div className="p-2.5 bg-pink-50/80 text-pink-600 rounded-xl shadow-sm border border-pink-100 relative">
                <Camera className="h-5 w-5" />
                {group.messages.length > 1 && (
                  <div className="absolute -top-2 -right-2 bg-slate-800 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full shadow">
                    {group.messages.length}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-start justify-between gap-4">
              <h3 className="font-bold text-slate-900 text-base flex-1 line-clamp-1" title={displayTitle}>
                {displayTitle}
              </h3>

              <div className="flex items-center gap-2">
                <Badge variant="outline" className={`shrink-0 gap-1 font-mono font-bold ${scoreVisual.badgeColor}`}>
                  {scoreVisual.icon}
                  {group.priority_score} 分
                </Badge>
                {isExpanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
              </div>
            </div>

            <div className="flex items-center flex-wrap gap-2 text-xs text-slate-500">
              <span className="font-medium">{latestMessage?.sender || group.external_sender_id}</span>
              <span>•</span>
              <span>{receivedTime}</span>

              {displayCategory && (
                <>
                  <span>•</span>
                  <Badge variant="outline" className="text-[10px] px-1.5 h-5 bg-white/60 text-slate-500 border-slate-200">
                    <Tag className="w-3 h-3 mr-1" />
                    {displayCategory}
                  </Badge>
                </>
              )}

              {!localIsRead && (
                <>
                  <span>•</span>
                  <span className="flex items-center gap-1 text-blue-600 font-semibold">
                    <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse" /> 未读
                  </span>
                </>
              )}
            </div>

            {!isExpanded && (
              <p className="text-sm text-slate-700 line-clamp-1 mt-2">
                {contentPreview}
              </p>
            )}
          </div>
        </div>

        {/* 展开内容明细 */}
        {isExpanded && (
          <div className="mt-2 pt-4 border-t border-slate-200/60 animate-in fade-in slide-in-from-top-2">
            {isEmail ? (
              <div className="bg-white/80 p-4 rounded-xl border border-slate-100 space-y-4 shadow-sm">
                {latestMessage?.email_analysis?.summary && (
                  <div className="text-sm font-semibold text-blue-800 bg-blue-50 p-3 rounded-lg border border-blue-100 flex items-start gap-2">
                    <Sparkles className="h-4 w-4 mt-0.5 shrink-0 text-blue-600" />
                    <span className="leading-relaxed">AI 摘要：{latestMessage.email_analysis.summary}</span>
                  </div>
                )}
                <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {latestMessage?.cleaned_content}
                </div>
              </div>
            ) : (
              <div className="bg-white/80 p-4 rounded-xl border border-slate-100 space-y-3 max-h-[300px] overflow-y-auto shadow-sm">
                <div className="text-xs text-center text-slate-400 mb-4 pb-2 border-b border-slate-100">
                  <MessageCircle className="h-3 w-3 inline mr-1" /> 会话明细
                </div>

                {/* IM 模式下的 AI 摘要高亮 */}
                {imSummary && (
                  <div className="text-sm font-semibold text-pink-800 bg-pink-50 p-3 rounded-lg border border-pink-100 flex items-start gap-2 mb-4">
                    <Sparkles className="h-4 w-4 mt-0.5 shrink-0 text-pink-600" />
                    <span className="leading-relaxed">AI 话题摘要：{imSummary}</span>
                  </div>
                )}

                {group.messages.map((msg, idx) => (
                  <div key={msg.id || idx} className={`flex ${msg.is_from_me ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] p-3 text-sm shadow-sm ${
                      msg.is_from_me 
                        ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm' 
                        : 'bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-tl-sm'
                    }`}>
                      {msg.cleaned_content}
                      <div className={`text-[10px] mt-1 text-right ${msg.is_from_me ? 'text-blue-200' : 'text-slate-400'}`}>
                        {msg.received_at ? new Date(msg.received_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>

      <div className={`border-t border-slate-200/60 px-5 py-2.5 flex items-center justify-between transition-opacity ${isExpanded ? 'bg-slate-50/50 opacity-100' : 'bg-transparent opacity-100 md:opacity-0 md:group-hover:opacity-100'}`}>
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-500 font-medium mr-2 hidden sm:inline-block">AI 評估準確嗎？</span>
          <Button variant="ghost" size="icon" onClick={(e) => handleFeedback(e, 10)} disabled={isSubmitting} className={`h-8 w-8 ${localFeedback === 10 ? 'text-green-700 bg-green-100/50' : 'text-slate-400 hover:text-green-600'}`}>
            <ThumbsUp className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={(e) => handleFeedback(e, 1)} disabled={isSubmitting} className={`h-8 w-8 ${localFeedback === 1 ? 'text-red-700 bg-red-100/50' : 'text-slate-400 hover:text-green-600'}`}>
            <ThumbsDown className="h-4 w-4" />
          </Button>
        </div>

        {/* 右侧组合功能按钮组 */}
        <div className="flex items-center gap-2">
          {/* 💥 当本地状态为已读时，动态渲染“标记为未读”按钮 */}
          {localIsRead && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleMarkUnread}
              className="h-8 text-xs border-slate-200 hover:bg-slate-100 bg-white text-slate-600 transition-all shadow-sm"
            >
              标记为未读
            </Button>
          )}

          <Button variant="outline" size="sm" onClick={handleArchive} disabled={isArchiving} className="h-8 text-xs gap-1.5 border-slate-200 hover:bg-slate-100 bg-white">
            {isArchiving ? <CheckCircle2 className="h-3.5 w-3.5 text-green-500" /> : <Archive className="h-3.5 w-3.5" />}
            {isArchiving ? "处理中..." : (isArchived ? "取消归档" : "归档全组")}
          </Button>
        </div>
      </div>
    </Card>
  );
}