// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { MainLayout } from "./components/layout/MainLayout";
import AccountDashboard from "./pages/AccountDashboard";
import NotificationInbox from "./pages/NotificationInbox";
import PreferenceSettings from "./pages/PreferenceSettings"; // 💥 引入刚刚写好的偏好设置页面

function App() {
  return (
    <BrowserRouter>
      {/* Layout 包裹 Routes 实现了侧边栏的持久挂载 */}
      <MainLayout>
        <Routes>
          {/* 自动重定向 */}
          <Route path="/" element={<Navigate to="/accounts" replace />} />

          {/* 账号设置页面 */}
          <Route path="/accounts" element={<AccountDashboard />} />

          {/* 消息看板页面 */}
          <Route path="/inbox" element={<NotificationInbox />} />

          {/* 💥 评分规则页面：正式挂载 */}
          <Route path="/rules" element={<PreferenceSettings />} />

          {/* 未来扩展页面 */}
          <Route path="/settings" element={<div className="p-8">系统设置开发中...</div>} />
        </Routes>
      </MainLayout>
    </BrowserRouter>
  );
}

export default App;