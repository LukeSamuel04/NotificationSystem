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
  accountPlatform?: string;
}

// 💥 滑块的真实值 (0-100) 转换为业务分值 (0.0 - 10.0)
const toActualValue = (sliderVal: number) => {
  if (sliderVal <= 50) return Number((sliderVal / 50).toFixed(1));
  return Number((1.0 + ((sliderVal - 50) / 50) * 9.0).toFixed(1));
};

// 💥 业务分值 (0.0 - 10.0) 还原为滑块的真实值 (0-100)
const toSliderValue = (actualVal: number) => {
  if (actualVal <= 1.0) return actualVal * 50;
  return 50 + ((actualVal - 1.0) / 9.0) * 50;
};

export function PreferenceModal({ isOpen, onClose, onSave, editingData, accountId, accountPlatform }: PreferenceModalProps) {
  const [formData, setFormData] = useState<Partial<UserPreferenceBase>>({
    platform: "email",
    preference_type: "sender_id",
    target_value: "",
    preference_factor: 1.0,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (editingData) {
      setFormData({
        platform: editingData.platform,
        preference_type: editingData.preference_type,
        target_value: editingData.target_value,
        preference_factor: editingData.preference_factor,
      });
    } else {
      // 动态适配新建规则时的默认选中平台
      let defaultPlatform = "global";
      if (accountPlatform === "email" || accountPlatform === "instagram") {
        defaultPlatform = accountPlatform;
      } else if (!accountPlatform || accountPlatform === "all") {
        defaultPlatform = "email";
      }

      setFormData({
        platform: defaultPlatform as "email" | "instagram" | "global",
        preference_type: "sender_id",
        target_value: "",
        preference_factor: 1.0,
      });
    }
    setErrorMsg(null);
  }, [editingData, isOpen, accountPlatform]);

  const handleSubmit = async () => {
    if (!formData.target_value) {
      setErrorMsg("目标匹配值不能为空");
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await onSave({ ...formData, account_id: accountId });
      onClose();
    } catch (error: any) {
      console.error("保存规则失败", error);
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
          {errorMsg && (
            <div className="flex items-start gap-2 p-3 text-sm text-red-600 bg-red-50 rounded-md border border-red-100">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span className="leading-tight">{errorMsg}</span>
            </div>
          )}

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
                {/* 💥 核心修复：如果在 Email 账号下，直接把 Instagram 选项物理移除！ */}
                {accountPlatform !== "instagram" && (
                  <SelectItem value="email">Email (邮件)</SelectItem>
                )}
                {accountPlatform !== "email" && (
                  <SelectItem value="instagram">Instagram (消息)</SelectItem>
                )}
                <SelectItem value="global">Global (全平台通用)</SelectItem>
              </SelectContent>
            </Select>
          </div>

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

          <div className="grid gap-2">
            <Label>目标匹配值</Label>
            <Input
              placeholder="例如: boss@bth.se 或 紧急"
              value={formData.target_value}
              onChange={(e) => setFormData({...formData, target_value: e.target.value})}
            />
          </div>

          <div className="grid gap-4">
            <div className="flex justify-between items-center">
              <Label>权重因子系数</Label>
              <span className="text-sm font-bold text-primary bg-primary/10 px-2 py-1 rounded">
                {formData.preference_factor?.toFixed(1)}x
              </span>
            </div>
            {/* 💥 核心修复：底层走 0-100，利用映射算法计算出完美的中间值 */}
            <Slider
              value={[toSliderValue(formData.preference_factor ?? 1.0)]}
              max={100}
              step={1}
              onValueChange={(vals) => setFormData({...formData, preference_factor: toActualValue(vals[0])})}
            />
            <div className="flex justify-between text-[10px] text-slate-400 px-1 mt-1">
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