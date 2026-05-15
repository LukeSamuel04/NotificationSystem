// src/pages/PreferenceSettings.tsx
import { useState, useEffect, useCallback } from "react";
import {
  Settings2,
  Plus,
  UserCircle,
  Tag,
  Globe,
  ListFilter,
  Loader2,
  AlertCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PreferenceTable } from "@/components/preference/PreferenceTable";
import { PreferenceModal } from "@/components/preference/PreferenceModal";
import { preferenceApi } from "@/api/preference";
import { accountApi } from "@/api/account";
import type { UserPreferenceResponse } from "@/types/preference";
import type { AccountResponse } from "@/types/account";

export default function PreferenceSettings() {
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [preferences, setPreferences] = useState<UserPreferenceResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<string>("all");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingData, setEditingData] = useState<UserPreferenceResponse | null>(null);

  useEffect(() => {
    const loadAccounts = async () => {
      try {
        const data = await accountApi.getAccounts();
        setAccounts(data || []);
        if (data && data.length > 0) {
          setSelectedAccountId(String(data[0].id));
        }
      } catch (error) {
        console.error("加载账号失败", error);
        setError("无法加载账号列表，请检查网络");
      }
    };
    loadAccounts();
  }, []);

  const fetchPreferences = useCallback(async () => {
    if (!selectedAccountId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await preferenceApi.getPreferences(selectedAccountId);
      if (Array.isArray(data)) {
        setPreferences(data);
      } else {
        setPreferences([]);
      }
    } catch (error) {
      console.error("获取规则流失败", error);
      setError("加载规则列表失败");
      setPreferences([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedAccountId]);

  useEffect(() => {
    fetchPreferences();
  }, [fetchPreferences]);

  const handleSave = async (payload: any) => {
    try {
      if (editingData) {
        await preferenceApi.updatePreference(editingData.id, {
          target_value: payload.target_value,
          preference_factor: payload.preference_factor
        });
      } else {
        await preferenceApi.createPreference(payload);
      }
      fetchPreferences();
    } catch (error) {
      console.error("保存失败", error);
      throw error;
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定要删除这条规则吗？这将影响 AI 对该类消息的评分。")) return;
    try {
      await preferenceApi.deletePreference(id);
      setPreferences(prev => prev.filter(p => p.id !== id));
    } catch (error) {
      console.error("删除失败", error);
    }
  };

  const handleEdit = (pref: UserPreferenceResponse) => {
    setEditingData(pref);
    setIsModalOpen(true);
  };

  const handleAddNew = () => {
    setEditingData(null);
    setIsModalOpen(true);
  };

  const safePreferences = Array.isArray(preferences) ? preferences : [];
  const filteredPreferences = safePreferences.filter(p =>
    activeTab === "all" ? true : p.preference_type === activeTab
  );

  // 💥 获取当前选中账号的平台类型，用于传给弹窗过滤选项
  const selectedAccount = accounts.find(a => String(a.id) === selectedAccountId);
  const currentPlatform = selectedAccount ? selectedAccount.platform : "all";

  return (
    <div className="container mx-auto py-8 px-4 max-w-5xl animate-in fade-in duration-500">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
          <Settings2 className="h-8 w-8 text-primary" />
          偏好规则自定义
        </h1>
        <p className="text-slate-500 mt-1">
          透过设定匹配维度与权重因子，你可以精确地引导 AI 算分模型。
        </p>
      </div>

      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm mb-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-600">当前配置账号:</span>
            <Select value={selectedAccountId} onValueChange={setSelectedAccountId}>
              <SelectTrigger className="w-[240px] bg-slate-50 border-slate-200">
                <SelectValue placeholder="请选择账号" />
              </SelectTrigger>
              <SelectContent>
                {accounts.map(acc => (
                  <SelectItem key={acc.id} value={String(acc.id)}>
                    <span className="flex items-center gap-2">
                      {acc.username} <span className="text-[10px] opacity-50 capitalize">({acc.platform})</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button onClick={handleAddNew} className="gap-2 shadow-sm">
            <Plus className="w-4 h-4" /> 新增偏好规则
          </Button>
        </div>

        <div className="h-px bg-slate-100 w-full" />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full sm:w-auto">
            <TabsList className="bg-slate-100/80 p-1">
              <TabsTrigger value="all" className="gap-2">
                <ListFilter className="w-3.5 h-3.5" /> 全部
              </TabsTrigger>
              <TabsTrigger value="sender_id" className="gap-2">
                <UserCircle className="w-3.5 h-3.5" /> 按发件人
              </TabsTrigger>
              <TabsTrigger value="topic" className="gap-2">
                <Tag className="w-3.5 h-3.5" /> 按话题
              </TabsTrigger>
              <TabsTrigger value="email_domain" className="gap-2">
                <Globe className="w-3.5 h-3.5" /> 按域名
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="text-xs text-slate-400 font-medium">
            当前分类共有 {filteredPreferences.length} 条规则
          </div>
        </div>
      </div>

      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 bg-white/50 backdrop-blur-sm z-10 flex items-center justify-center rounded-xl">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-4 mb-4 text-sm text-red-800 bg-red-50 rounded-lg border border-red-100">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}

        <PreferenceTable
          preferences={filteredPreferences}
          onEdit={handleEdit}
          onDelete={handleDelete}
          isLoading={isLoading}
        />
      </div>

      {/* 💥 弹窗：将 currentPlatform 传入 */}
      <PreferenceModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSave}
        editingData={editingData}
        accountId={selectedAccountId}
        accountPlatform={currentPlatform}
      />
    </div>
  );
}