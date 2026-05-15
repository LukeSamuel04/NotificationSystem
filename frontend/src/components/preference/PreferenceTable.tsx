// src/components/preference/PreferenceTable.tsx
import { Edit2, Trash2, Mail, Camera, Globe, Info } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { UserPreferenceResponse } from "@/types/preference";

interface PreferenceTableProps {
  preferences: UserPreferenceResponse[];
  onEdit: (pref: UserPreferenceResponse) => void;
  onDelete: (id: number) => void;
  isLoading: boolean;
}

const TYPE_LABELS: Record<string, string> = {
  sender_id: "发件人 ID",
  topic: "话题关键词",
  email_domain: "邮件域名"
};

// 💥 同步弹窗的滑块视觉算法，确保证列表进度条的 50% 完美对应 1.0 分
const toSliderValue = (actualVal: number) => {
  if (actualVal <= 1.0) {
    return actualVal * 50;
  } else {
    return 50 + ((actualVal - 1.0) / 9.0) * 50;
  }
};

export function PreferenceTable({ preferences, onEdit, onDelete, isLoading }: PreferenceTableProps) {

  const getFactorColor = (factor: number) => {
    if (factor === 0) return "bg-slate-300";
    if (factor < 1) return "bg-blue-400";
    if (factor === 1) return "bg-green-400";
    if (factor < 5) return "bg-orange-400";
    return "bg-red-500";
  };

  if (!isLoading && preferences.length === 0) {
    return (
      <div className="text-center py-20 border-2 border-dashed rounded-xl border-slate-100">
        <div className="bg-slate-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4">
          <Info className="text-slate-400 w-6 h-6" />
        </div>
        <p className="text-slate-500">当前分类下暂无偏好规则</p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-slate-200 bg-white overflow-hidden">
      <Table>
        <TableHeader className="bg-slate-50/50">
          <TableRow>
            <TableHead className="w-[100px]">平台</TableHead>
            <TableHead className="w-[120px]">匹配维度</TableHead>
            <TableHead>目标关键词 / 值</TableHead>
            <TableHead className="w-[200px]">权重因子 (影响评分)</TableHead>
            <TableHead className="w-[100px] text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {preferences.map((pref) => (
            <TableRow key={pref.id} className="hover:bg-slate-50/50 transition-colors">
              <TableCell>
                <div className="flex items-center gap-2">
                  {pref.platform === 'email' && <Mail className="w-4 h-4 text-blue-500" />}
                  {pref.platform === 'instagram' && <Camera className="w-4 h-4 text-pink-500" />}
                  {pref.platform === 'global' && <Globe className="w-4 h-4 text-slate-500" />}
                  <span className="capitalize text-xs font-medium">{pref.platform}</span>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant="secondary" className="font-normal text-[11px]">
                  {TYPE_LABELS[pref.preference_type]}
                </Badge>
              </TableCell>
              <TableCell className="font-mono text-sm text-slate-700">
                {pref.target_value}
              </TableCell>
              <TableCell>
                <div className="flex flex-col gap-1.5">
                  <div className="flex justify-between text-[10px] font-bold text-slate-400">
                    <span>{pref.preference_factor.toFixed(1)}x</span>
                    <span>{pref.preference_factor === 0 ? "已屏蔽" : pref.preference_factor > 1 ? "提权" : "降权"}</span>
                  </div>
                  <Progress
                    value={toSliderValue(pref.preference_factor)}
                    className="h-1.5"
                    // @ts-ignore
                    indicatorClassName={getFactorColor(pref.preference_factor)}
                  />
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onEdit(pref)}
                    className="h-8 w-8 text-slate-400 hover:text-blue-600"
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onDelete(pref.id)}
                    className="h-8 w-8 text-slate-400 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}