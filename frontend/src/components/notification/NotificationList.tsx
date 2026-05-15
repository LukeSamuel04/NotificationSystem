import { Inbox, Sparkles } from "lucide-react";
import { NotificationCard } from "./NotificationCard";
import type { GroupedNotification } from "@/types/notification";

interface NotificationListProps {
  notifications: GroupedNotification[]; // 💥 修改类型
  isLoading: boolean;
  onRefresh: () => void;
}

export function NotificationList({ notifications, isLoading, onRefresh }: NotificationListProps) {

  if (isLoading) {
    return (
      <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-white rounded-xl border border-slate-100 shadow-sm animate-pulse flex p-5 gap-4">
            <div className="w-10 h-10 bg-slate-200 rounded-xl shrink-0" />
            <div className="flex-1 space-y-3 py-1">
              <div className="flex justify-between">
                <div className="h-4 bg-slate-200 rounded w-1/3" />
                <div className="h-5 bg-slate-200 rounded-full w-16" />
              </div>
              <div className="h-3 bg-slate-100 rounded w-1/4" />
              <div className="space-y-2 pt-2">
                <div className="h-3 bg-slate-100 rounded w-full" />
                <div className="h-3 bg-slate-100 rounded w-4/5" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (notifications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4 text-center animate-in zoom-in-95 duration-500">
        <div className="relative mb-6">
          <div className="absolute inset-0 bg-blue-100 blur-2xl rounded-full opacity-50" />
          <div className="relative bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
            <Inbox className="h-12 w-12 text-slate-300" strokeWidth={1.5} />
            <Sparkles className="absolute -top-2 -right-2 h-6 w-6 text-yellow-400 animate-bounce" />
          </div>
        </div>
        <h3 className="text-lg font-bold text-slate-900 mb-2">Inbox Zero!</h3>
        <p className="text-slate-500 max-w-[250px]">
          AI 探针暂未发现新的高优先级情报。去喝杯咖啡休息一下吧 ☕️
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {notifications.map((group) => (
        <NotificationCard
          key={group.id}
          group={group} // 💥 传入聚合体
          onUpdate={onRefresh}
        />
      ))}
    </div>
  );
}