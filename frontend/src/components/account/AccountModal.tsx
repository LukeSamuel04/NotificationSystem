import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { AccountForm } from "./AccountForm";
import { accountApi } from "@/api/account";
import type { AccountResponse } from "@/types/account";

interface AccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  accountToEdit: AccountResponse | null;
  onRefresh: () => void;
}

export function AccountModal({ isOpen, onClose, accountToEdit, onRefresh }: AccountModalProps) {

  const handleSubmit = async (payload: any) => {
    // 💥 关键改动：不再在这里 catch 错误，而是让它向上抛出给 Form 处理
    if (accountToEdit) {
      // 这里的 PUT 请求会触发后端探针
      await accountApi.updateAccount(accountToEdit.id, payload);
    } else {
      // 这里的 POST 请求会触发后端探针
      await accountApi.createAccount(payload);
    }

    // 只有在 API 成功响应（200 OK）后才会执行下面代码
    onRefresh();
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[550px] gap-0">
        <DialogHeader className="p-6 pb-2">
          <DialogTitle className="text-xl font-bold">
            {accountToEdit ? "编辑探针配置" : "接入新消息源"}
          </DialogTitle>
        </DialogHeader>

        <div className="px-6">
          {isOpen && (
            <AccountForm
              initialData={accountToEdit}
              onSubmit={handleSubmit}
              onCancel={onClose}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}