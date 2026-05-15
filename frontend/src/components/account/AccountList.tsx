import type { AccountResponse } from "@/types/account";
import { AccountCard } from "./AccountCard";
import { Inbox } from "lucide-react";

interface AccountListProps {
  accounts: AccountResponse[];
  onRefresh: () => void;
  onEdit: (account: AccountResponse) => void;
}

export function AccountList({ accounts, onRefresh, onEdit }: AccountListProps) {
  if (!accounts || accounts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-16 text-center border-2 rounded-xl border-dashed border-slate-200 bg-slate-50">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 mb-4 shadow-sm">
          <Inbox className="h-8 w-8 text-slate-400" />
        </div>
        <h3 className="text-lg font-semibold text-slate-900">暂无绑定的账号</h3>
        <p className="text-sm text-slate-500 mt-2 max-w-sm">
          你还没有添加任何 Email 或 Instagram 账号。点击“添加账号”开始配置你的消息探针。
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {accounts.map((account) => (
        <AccountCard
          key={account.id}
          account={account}
          onRefresh={onRefresh}
          onEdit={onEdit}
        />
      ))}
    </div>
  );
}