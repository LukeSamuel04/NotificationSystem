import { Inbox, Archive, Mail, Camera, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AccountResponse } from "@/types/account";

interface NotificationFiltersProps {
  // 供筛选器渲染使用的账号列表
  accounts: AccountResponse[];

  // 状态 1：收件箱 vs 归档
  status: "processed" | "archived";
  onStatusChange: (status: "processed" | "archived") => void;

  // 状态 2：账号隔离
  accountId: string | "all";
  onAccountChange: (id: string | "all") => void;

  // 状态 3：未读过滤器
  unreadOnly: boolean;
  onUnreadChange: (unread: boolean) => void;

  // 加载状态，用于在请求时禁用筛选器防止竞态问题
  isLoading: boolean;
}

export function NotificationFilters({
  accounts,
  status,
  onStatusChange,
  accountId,
  onAccountChange,
  unreadOnly,
  onUnreadChange,
  isLoading
}: NotificationFiltersProps) {

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all">

      {/* 左侧：核心状态视图切换 (Pills) */}
      <div className="flex bg-slate-100 p-1 rounded-lg w-fit">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onStatusChange("processed")}
          disabled={isLoading}
          className={`h-8 px-4 gap-2 rounded-md transition-all ${
            status === "processed" 
              ? "bg-white text-slate-900 shadow-sm hover:bg-white" 
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          <Inbox className="h-4 w-4" />
          优先收件箱
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onStatusChange("archived")}
          disabled={isLoading}
          className={`h-8 px-4 gap-2 rounded-md transition-all ${
            status === "archived" 
              ? "bg-white text-slate-900 shadow-sm hover:bg-white" 
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          <Archive className="h-4 w-4" />
          已归档
        </Button>
      </div>

      {/* 右侧：精细化组合筛选 */}
      <div className="flex items-center gap-4">

        {/* 未读开关 */}
        <div className="flex items-center gap-2 pr-4 border-r border-slate-200">
          <Switch
            id="unread-mode"
            checked={unreadOnly}
            onCheckedChange={onUnreadChange}
            disabled={isLoading}
          />
          <label
            htmlFor="unread-mode"
            className="text-sm font-medium text-slate-600 cursor-pointer select-none"
          >
            仅看未读
          </label>
        </div>

        {/* 账号过滤器 (下拉菜单) */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <Select
            value={accountId}
            onValueChange={onAccountChange}
            disabled={isLoading}
          >
            <SelectTrigger className="w-[180px] h-9 bg-slate-50 border-slate-200 text-sm">
              <SelectValue placeholder="选择消息源" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" className="font-medium">
                聚合全视界 (All)
              </SelectItem>
              {accounts.map((acc) => (
                <SelectItem key={acc.id} value={acc.id}>
                  <div className="flex items-center gap-2">
                    {acc.platform === "email" ? (
                      <Mail className="h-3.5 w-3.5 text-blue-500" />
                    ) : (
                      <Camera className="h-3.5 w-3.5 text-pink-500" />
                    )}
                    <span className="truncate max-w-[100px]">{acc.username}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

      </div>
    </div>
  );
}