import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import './App.css';
import DashboardPage from './pages/DashboardPage.tsx';
import ManualInputPage from './pages/ManualInputPage';
import HistoryPage from './pages/HistoryPage';
import { LayoutDashboard, PenLine, Archive } from 'lucide-react'; // 新增 Archive

function App() {
  return (
    <Router>
      <div className="app-container" style={{ display: 'flex', height: '100vh', backgroundColor: '#f8fafc', overflow: 'hidden' }}>

        {/* ================= 左侧全局导航栏 ================= */}
        <aside style={{
          width: '80px', backgroundColor: '#1e293b', display: 'flex',
          flexDirection: 'column', alignItems: 'center', padding: '20px 0', gap: '30px',
          flexShrink: 0,
          boxShadow: '2px 0 10px rgba(0,0,0,0.1)', zIndex: 10
        }}>
          {/* LOGO */}
          <div style={{ color: 'white', marginBottom: '10px' }}>
            <div style={{ width: '40px', height: '40px', backgroundColor: '#3b82f6', borderRadius: '10px', display: 'flex', justifyContent: 'center', alignItems: 'center', fontWeight: 'bold', fontSize: '18px', boxShadow: '0 4px 6px rgba(59, 130, 246, 0.3)' }}>
              NS
            </div>
          </div>

          {/* 看板路由按钮 */}
          <NavLink
            to="/kanban"
            style={({ isActive }) => ({
              color: isActive ? '#3b82f6' : '#94a3b8',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px',
              textDecoration: 'none', fontSize: '12px', transition: 'color 0.2s', fontWeight: isActive ? 'bold' : 'normal'
            })}
          >
            <LayoutDashboard size={24} />
            <span>Kanban</span>
          </NavLink>

          {/* 录入路由按钮 */}
          <NavLink
            to="/manual"
            style={({ isActive }) => ({
              color: isActive ? '#3b82f6' : '#94a3b8',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px',
              textDecoration: 'none', fontSize: '12px', transition: 'color 0.2s', fontWeight: isActive ? 'bold' : 'normal'
            })}
          >
            <PenLine size={24} />
            <span>Input</span>
          </NavLink>
          <NavLink
         to="/history"
         style={({ isActive }) => ({
           color: isActive ? '#3b82f6' : '#94a3b8',
           display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px',
           textDecoration: 'none', fontSize: '12px', transition: 'color 0.2s', fontWeight: isActive ? 'bold' : 'normal'
         })}
       >
         <Archive size={24} />
         <span>History</span>
         </NavLink>
        </aside>

        {/* ================= 右侧动态视图区 ================= */}
        <main style={{ flex: 1, position: 'relative' }}>
          <Routes>
            <Route path="/kanban" element={<DashboardPage />} />
            <Route path="/manual" element={<ManualInputPage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Routes>
        </main>

      </div>
    </Router>
  );
}

export default App;