import axios from 'axios';

// 后端基础地址
const API_BASE_URL = 'http://127.0.0.1:8000';

export const notificationApi = {
  // 对应 collector.py 中的 @router.post("/collect")
  collect: (data: { sender: string; subject: string; raw_content: string }) =>
    axios.post(`${API_BASE_URL}/collect`, data),

  // 对应我们在 collector.py 新增的 @router.get("/notifications")
  getNotifications: () =>
    axios.get(`${API_BASE_URL}/notifications`),

  // 【新增】：对应 collector.py 中的 @router.patch("/{notif_id}/done")
  markAsDone: (id: number) =>
    axios.patch(`${API_BASE_URL}/${id}/done`),
  getHistory: () => {
    return axios.get(`${API_BASE_URL}/history`);
  },
  restoreNotification: (id: number) => {
    return axios.patch(`${API_BASE_URL}/${id}/restore`);
  }
};