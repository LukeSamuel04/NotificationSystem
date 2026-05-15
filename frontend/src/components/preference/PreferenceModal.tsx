// src/components/preference/PreferenceModal.tsx
import { useState, useEffect } from "react";
import { AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { UserPreferenceResponse, UserPreferenceBase } from "@/types/preference";

interface PreferenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: any) => Promise<void>;
  editingData: UserPreferenceResponse | null;
  accountId: string;
}

export function PreferenceModal({ isOpen, onClose, onSave, editingData, accountId }: PreferenceModalProps) {
  const [formData, setFormData] = useState<Partial<UserPreferenceBase>>({
    platform: "email",
    preference_type: "sender_id",
    target_value: "",
    preference_factor: 1.0,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null); // 💥 新增错误状态存储

  // 当进入编辑模式时，回填数据
  useEffect(() => {
    if (editingData) {
      setFormData({
        platform: editingData.platform,
        preference_type: editingData.preference_type,
        target_value: editingData.target_value,
        preference_factor: editingData.preference_factor,
      });
    } else {
      setFormData({
        platform: "email",
        preference_type: "sender_id",
        target_value: "",
        preference_factor: 1.0,
      });
    }
    setErrorMsg(null); // 每次打开弹窗清空错误
  }, [editingData, isOpen]);

  const handleSubmit = async () => {
    if (!formData.target_value) {
      setErrorMsg("目标匹配值不能为空");
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null); // 提交前清空旧报错
    try {
      await onSave({ ...formData, account_id: accountId });
      onClose();
    } catch (error: any) {
      console.error("保存规则失败", error);
      // 💥 拦截 Axios 错误，提取后端 FastAPI 吐出的详情并显示在 UI 上
      const backendMsg = error.response?.data?.detail || error.message || "请求后端失败，请检查网络";
      setErrorMsg(typeof backendMsg === 'string' ? backendMsg : JSON.stringify(backendMsg));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{editingData ? "编辑偏好规则" : "新增偏好规则"}</DialogTitle>
          <DialogDescription>
            自定义 AI 评分权重。0.0 为完全屏蔽，1.0 为默认，10.0 为极高优先级。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* 💥 错误提示条：有报错时自动出现 */}
          {errorMsg && (
            <div className="flex items-start gap-2 p-3 text-sm text-red-600 bg-red-50 rounded-md border border-red-100">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span className="leading-tight">{errorMsg}</span>
            </div>
          )}

          {/* 平台选择 */}
          <div className="grid gap-2">
            <Label>作用平台</Label>
            <Select
              value={formData.platform}
              onValueChange={(v: any) => setFormData({...formData, platform: v})}
              disabled={!!editingData}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择平台" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="email">Email (邮件)</SelectItem>
                <SelectItem value="instagram">Instagram (消息)</SelectItem>
                <SelectItem value="global">Global (全平台通用)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 维度选择 */}
          <div className="grid gap-2">
            <Label>匹配维度</Label>
            <Select
              value={formData.preference_type}
              onValueChange={(v: any) => setFormData({...formData, preference_type: v})}
              disabled={!!editingData}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择维度" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sender_id">发件人 ID / 账号名</SelectItem>
                <SelectItem value="topic">话题关键词 (AI 提取)</SelectItem>
                <SelectItem value="email_domain">邮件后缀域名 (如 @bth.se)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 目标值 */}
          <div className="grid gap-2">
            <Label>目标匹配值</Label>
            <Input
              placeholder="例如: boss@bth.se 或 紧急"
              value={formData.target_value}
              onChange={(e) => setFormData({...formData, target_value: e.target.value})}
            />
          </div>

          {/* 权重因子滑动条 */}
          <div className="grid gap-4">
            <div className="flex justify-between items-center">
              <Label>权重因子系数</Label>
              <span className="text-sm font-bold text-primary bg-primary/10 px-2 py-1 rounded">
                {formData.preference_factor?.toFixed(1)}x
              </span>
            </div>
            <Slider
              value={[formData.preference_factor || 1.0]}
              max={10}
              step={0.1}
              onValueChange={(vals) => setFormData({...formData, preference_factor: vals[0]})}
            />
            <div className="flex justify-between text-[10px] text-slate-400 px-1">
              <span>屏蔽 (0.0)</span>
              <span>默认 (1.0)</span>
              <span>极紧急 (10.0)</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>取消</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "保存中..." : "确认保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}