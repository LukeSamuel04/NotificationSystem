import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Mail, Camera, Edit2, Activity } from "lucide-react";
import type { AccountResponse } from "@/types/account";

// 💥 解开了 API 调用的封印
import { accountApi } from "@/api/account";

interface AccountCardProps {
  account: AccountResponse;
  onRefresh: () => void;
  onEdit: (account: AccountResponse) => void;
}

export function AccountCard({ account, onRefresh, onEdit }: AccountCardProps) {
  const [loading, setLoading] = useState(false);

  const handleToggle = async (checked: boolean) => {
    setLoading(true);
    try {
      // 💥 真正调用后端的 PATCH 接口，翻转数据库中的激活状态
      await accountApi.toggleAccount(account.id, checked);

      // 后端更新成功后，触发外层页面重新拉取最新数据
      onRefresh();
    } catch (error) {
      console.error("切换状态失败:", error);
    } finally {
      setLoading(false);
    }
  };

  const isEmail = account.platform === "email";

  return (
    <Card className="overflow-hidden transition-all hover:shadow-md border-slate-200">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3 bg-slate-50/50">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          {isEmail ? (
            <Mail className="h-5 w-5 text-blue-500" />
          ) : (
            <Camera className="h-5 w-5 text-pink-500" />
          )}
          <span className="truncate max-w-[150px]" title={account.username}>
            {account.username}
          </span>
        </CardTitle>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => onEdit(account)} className="h-8 w-8 text-slate-500 hover:text-slate-900">
            <Edit2 className="h-4 w-4" />
          </Button>
          <Switch checked={account.is_active} onCheckedChange={handleToggle} disabled={loading} />
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="flex flex-col gap-2">
          <div className="flex justify-between items-center text-sm">
            <span className="text-slate-500">Platform ID:</span>
            <span className="font-medium text-slate-700 truncate max-w-[120px]" title={account.platform_account_id}>
              {account.platform_account_id}
            </span>
          </div>
          <div className="flex justify-between items-center text-sm mt-1">
            <span className="text-slate-500 flex items-center gap-1">
              <Activity className="h-4 w-4" /> 状态验证:
            </span>
            <div className="flex items-center gap-1.5">
              <div className={`h-2.5 w-2.5 rounded-full ${account.is_valid ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} />
              <span className={`text-xs font-bold uppercase tracking-wider ${account.is_valid ? 'text-green-600' : 'text-red-600'}`}>
                {account.is_valid ? "Connected" : "Error"}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}