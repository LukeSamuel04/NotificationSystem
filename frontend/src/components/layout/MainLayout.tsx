import type { ReactNode } from "react";
import {
  LayoutDashboard,
  Settings,
  BellRing,
  ShieldCheck,
  Menu
} from "lucide-react";
import { cn } from "@/lib/utils";
// 💥 引入 NavLink 用于导航
import { NavLink } from "react-router-dom";

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  // 为菜单项配置对应的路由路径
  const menuItems = [
    { icon: LayoutDashboard, label: "账号管理", path: "/accounts" },
    { icon: BellRing, label: "消息收件箱", path: "/inbox" },
    { icon: ShieldCheck, label: "评分规则", path: "/rules" },
    { icon: Settings, label: "系统设置", path: "/settings" },
  ];

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans">
      {/* 左侧固定侧边栏 */}
      <aside className="w-64 border-r bg-white hidden md:flex flex-col">
        <div className="p-6 border-b">
          <div className="flex items-center gap-3">
            <div className="bg-primary p-2 rounded-lg">
              <BellRing className="h-6 w-6 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight text-slate-900">
              AI Priority
            </span>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {menuItems.map((item) => (
            <NavLink
              key={item.label}
              to={item.path}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer transition-colors",
                isActive
                  ? "bg-slate-100 text-primary font-semibold shadow-sm"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t text-xs text-slate-400 text-center">
          v1.0.0-beta | BTH Dev
        </div>
      </aside>

      {/* 右侧主内容区 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 border-b bg-white flex items-center px-6 md:hidden justify-between">
          <Menu className="h-6 w-6 text-slate-500" />
          <span className="font-bold text-lg">AI Priority</span>
          <div className="w-6" />
        </header>

        {/* 💥 这里渲染具体的页面组件 */}
        <div className="flex-1 overflow-y-auto bg-slate-50">
          {children}
        </div>
      </main>
    </div>
  );
}