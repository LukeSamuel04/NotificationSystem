import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertCircle, Loader2 } from "lucide-react";
import type { AccountResponse, AccountCreatePayload, PlatformType, EmailConfig, InstagramConfig } from "@/types/account";

interface AccountFormProps {
  initialData?: AccountResponse | null;
  onSubmit: (payload: any) => Promise<void>;
  onCancel: () => void;
}

export function AccountForm({ initialData, onSubmit, onCancel }: AccountFormProps) {
  const isEdit = !!initialData;
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const [platform, setPlatform] = useState<PlatformType>(initialData?.platform || "email");
  const [username, setUsername] = useState(initialData?.username || "");
  const [platformAccountId, setPlatformAccountId] = useState(initialData?.platform_account_id || "");

  const [emailConfig, setEmailConfig] = useState<EmailConfig>({
    host: (initialData?.config as EmailConfig)?.host || "",
    port: (initialData?.config as EmailConfig)?.port || 993,
    password: "",
  });

  const [igConfig, setIgConfig] = useState<InstagramConfig>({
    access_token: "",
    proxy_url: (initialData?.config as InstagramConfig)?.proxy_url || "",
  });

  useEffect(() => {
    if (!isEdit) {
      setPlatformAccountId("");
      setUsername("");
    }
  }, [platform, isEdit]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setLocalError(null);

    try {
      const configPayload = platform === "email"
        ? { ...emailConfig }
        : { ...igConfig };

      // 增量更新逻辑：如果密码/Token为空，不发送该字段以避免后端覆盖为脏数据
      if (isEdit) {
        if (platform === "email" && !emailConfig.password) delete (configPayload as EmailConfig).password;
        if (platform === "instagram" && !igConfig.access_token) delete (configPayload as InstagramConfig).access_token;
      }

      const payload: AccountCreatePayload | any = {
        platform,
        username,
        platform_account_id: platformAccountId,
        is_active: initialData ? initialData.is_active : true,
        config: configPayload,
      };

      // 触发探针：等待后端验证结果
      await onSubmit(payload);
      // 成功则由 Modal 关闭，此处不写 onClose
    } catch (error: any) {
      // 捕捉探针验证失败产生的 400/401/500 错误
      const msg = error.response?.data?.detail || "探针验证失败，请检查账号密码或服务器配置";
      setLocalError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 py-4">
      {localError && (
        <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p className="font-medium">{localError}</p>
        </div>
      )}

      <div className="space-y-1.5">
        <label className="text-sm font-medium text-slate-700">平台类型</label>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="radio" value="email" checked={platform === "email"} onChange={() => setPlatform("email")} disabled={isEdit} />
            Email (IMAP)
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="radio" value="instagram" checked={platform === "instagram"} onChange={() => setPlatform("instagram")} disabled={isEdit} />
            Instagram Graph API
          </label>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700">账号 ID</label>
          <Input required value={platformAccountId} onChange={(e) => setPlatformAccountId(e.target.value)} disabled={isEdit} className="bg-slate-50" />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700">显示备注</label>
          <Input required value={username} onChange={(e) => setUsername(e.target.value)} placeholder="例如：主工作邮箱" />
        </div>
      </div>

      <div className="p-4 border rounded-xl bg-slate-50/50 space-y-4">
        <div className="flex items-center justify-between border-b pb-2">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">探针连接配置</h4>
        </div>

        {platform === "email" ? (
          <>
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2 space-y-1.5">
                <label className="text-sm font-medium text-slate-700">IMAP Host</label>
                <Input required value={emailConfig.host} onChange={(e) => setEmailConfig({...emailConfig, host: e.target.value})} placeholder="imap.gmail.com" />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Port</label>
                <Input required type="number" value={emailConfig.port} onChange={(e) => setEmailConfig({...emailConfig, port: Number(e.target.value)})} />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                {isEdit ? "更新应用密码 (留空保持不变)" : "应用专属密码"}
              </label>
              <Input type="password" required={!isEdit} value={emailConfig.password} onChange={(e) => setEmailConfig({...emailConfig, password: e.target.value})} />
            </div>
          </>
        ) : (
          <>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                {isEdit ? "更新 Access Token (留空保持不变)" : "长期 Access Token"}
              </label>
              <Input type="password" required={!isEdit} value={igConfig.access_token} onChange={(e) => setIgConfig({...igConfig, access_token: e.target.value})} />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">代理服务器 (可选)</label>
              <Input value={igConfig.proxy_url} onChange={(e) => setIgConfig({...igConfig, proxy_url: e.target.value})} placeholder="http://127.0.0.1:7890" />
            </div>
          </>
        )}
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="ghost" onClick={onCancel} disabled={loading}>
          取消
        </Button>
        <Button type="submit" disabled={loading} className="min-w-[120px]">
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              验证中...
            </>
          ) : (
            isEdit ? "确认更新" : "确认添加"
          )}
        </Button>
      </div>
    </form>
  );
}