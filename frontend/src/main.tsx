import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx' // 确保路径指向你的 App.tsx
import './App.css'     // 引入你存放所有样式的 App.css

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
