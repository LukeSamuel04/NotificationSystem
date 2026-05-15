import { useState, useEffect } from "react";
import { Plus, RefreshCw, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AccountList } from "@/components/account/AccountList";
import { AccountModal } from "@/components/account/AccountModal";
import { accountApi } from "@/api/account";
import type { AccountResponse } from "@/types/account";

export default function AccountDashboard() {
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 弹窗控制状态
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<AccountResponse | null>(null);

  // 初始化加载数据
  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    setIsLoading(true);
    try {
      // 对接真实的 FastAPI 后端
      const data = await accountApi.getAccounts();
      setAccounts(data);
    } catch (error) {
      console.error("加载账号列表失败:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // 处理“添加账号”点击
  const handleAddAccount = () => {
    setEditingAccount(null); // 确保不是编辑模式
    setIsModalOpen(true);
  };

  // 处理“编辑账号”点击
  const handleEditAccount = (account: AccountResponse) => {
    setEditingAccount(account);
    setIsModalOpen(true);
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      {/* 页面头部 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
            <LayoutDashboard className="h-8 w-8 text-primary" />
            账号管理大盘
          </h1>
          <p className="text-slate-500 mt-1">
            配置并监控你的消息源探针，为 AI 优先级系统提供原始数据流。
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={fetchAccounts}
            disabled={isLoading}
            className={isLoading ? "animate-spin" : ""}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={handleAddAccount} className="gap-2">
            <Plus className="h-4 w-4" /> 添加账号
          </Button>
        </div>
      </div>

      {/* 列表区域 */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 opacity-50 pointer-events-none">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 bg-slate-100 animate-pulse rounded-xl border border-slate-200" />
          ))}
        </div>
      ) : (
        <AccountList
          accounts={accounts}
          onRefresh={fetchAccounts}
          onEdit={handleEditAccount}
        />
      )}

      {/* 统一弹窗逻辑：负责新建和编辑 */}
      <AccountModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        accountToEdit={editingAccount}
        onRefresh={fetchAccounts}
      />
    </div>
  );
}