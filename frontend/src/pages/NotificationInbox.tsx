import { useState, useEffect, useCallback } from "react";
import { BellRing, RefreshCw, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NotificationFilters } from "@/components/notification/NotificationFilters";
import { NotificationList } from "@/components/notification/NotificationList";
import { notificationApi } from "@/api/notification";
import { accountApi } from "@/api/account";
import type { NotificationResponse, GroupedNotification } from "@/types/notification";
import type { AccountResponse } from "@/types/account";

const groupNotifications = (rawList: NotificationResponse[]): GroupedNotification[] => {
  const map = new Map<string, GroupedNotification>();

  rawList.forEach(notif => {
    if (notif.platform === 'email' && notif.is_from_me) {
      return;
    }

    const groupId = notif.platform === 'email'
      ? `email_${notif.id}`
      : `ig_${notif.account_id}_${notif.external_sender_id}`;

    if (!map.has(groupId)) {
      let title = "未知联系人";
      if (notif.platform === 'email') {
        title = notif.subject || notif.sender || "无主题邮件";
      } else {
        // 💥 核心修复：对接真实的 im_session_state 与 current_topic
        title = notif.im_session_state?.current_topic || notif.im_session_state?.summary_snapshot || notif.sender || "Instagram 交流";
      }

      map.set(groupId, {
        id: groupId,
        platform: notif.platform,
        account_id: notif.account_id,
        external_sender_id: notif.external_sender_id,
        messages: [],
        latest_received_at: notif.received_at || "",
        priority_score: notif.platform === 'email'
          ? (notif.email_analysis?.priority_score || 0)
          : (notif.im_session_state?.priority_score || 0), // 💥 核心修复：绑定正确的 IM 分数
        title: title,
        is_read: true
      });
    }

    const group = map.get(groupId)!;
    group.messages.push(notif);

    if (!notif.is_read) group.is_read = false;

    if (notif.received_at && notif.received_at > group.latest_received_at) {
      group.latest_received_at = notif.received_at;
    }
  });

  const groupedArray = Array.from(map.values());

  groupedArray.forEach(group => {
    if (group.platform === 'instagram') {
      group.messages.sort((a, b) => {
        const timeA = new Date(a.received_at || 0).getTime();
        const timeB = new Date(b.received_at || 0).getTime();
        return timeA - timeB;
      });
    }
  });

  groupedArray.sort((a, b) => {
    if (b.priority_score !== a.priority_score) return b.priority_score - a.priority_score;
    return new Date(b.latest_received_at).getTime() - new Date(a.latest_received_at).getTime();
  });

  return groupedArray;
};

export default function NotificationInbox() {
  const [groupedData, setGroupedData] = useState<GroupedNotification[]>([]);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [status, setStatus] = useState<"processed" | "archived">("processed");
  const [accountId, setAccountId] = useState<string | "all">("all");
  const [unreadOnly, setUnreadOnly] = useState(false);

  const fetchNotifications = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = {
        status,
        account_id: accountId === "all" ? undefined : accountId,
        is_read: unreadOnly ? false : undefined,
        limit: 100
      };
      const data = await notificationApi.getNotifications(params);
      const packagedData = groupNotifications(data);
      setGroupedData(packagedData);
    } catch (error) {
      console.error("获取通知流失败:", error);
    } finally {
      setIsLoading(false);
    }
  }, [status, accountId, unreadOnly]);

  const fetchAccounts = async () => {
    try {
      const data = await accountApi.getAccounts();
      setAccounts(data);
    } catch (error) {
      console.error("加载账号筛选列表失败:", error);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkAllRead = async () => {
    if (accountId === "all") return;
    try {
      await notificationApi.markAllAsRead(accountId);
      fetchNotifications();
    } catch (error) {
      console.error("批量已读失败:", error);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-5xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
            <BellRing className="h-8 w-8 text-primary" />
            AI 智能收件箱
          </h1>
          <p className="text-slate-500 mt-1">
            将碎片消息自动聚合成对话流，由 AI 提炼摘要并计算优先级评分。
          </p>
        </div>

        <div className="flex items-center gap-3">
          {status === "processed" && accountId !== "all" && (
            <Button variant="ghost" size="sm" onClick={handleMarkAllRead} className="text-slate-500 hover:text-primary gap-2">
              <CheckCheck className="h-4 w-4" /> 一键已读
            </Button>
          )}
          <Button variant="outline" size="icon" onClick={fetchNotifications} disabled={isLoading} className={`h-9 w-9 ${isLoading ? "animate-spin" : ""}`}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <NotificationFilters
        accounts={accounts}
        status={status}
        onStatusChange={setStatus}
        accountId={accountId}
        onAccountChange={setAccountId}
        unreadOnly={unreadOnly}
        onUnreadChange={setUnreadOnly}
        isLoading={isLoading}
      />

      <div className="min-h-[400px]">
        <NotificationList
          notifications={groupedData}
          isLoading={isLoading}
          onRefresh={fetchNotifications}
        />
      </div>

      <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
        <p>所有消息均已通过 SSL/TLS 加密，AI 评分仅在本地模型集群计算。</p>
        <p>当前聚合：{groupedData.length} 个交流 Session</p>
      </div>
    </div>
  );
}