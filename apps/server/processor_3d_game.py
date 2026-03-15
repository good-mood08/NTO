import numpy as np
import math
import cv2


class ARGame3D:
    def __init__(self):
        # Настройка AprilTag 16h5
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        # --- ПАМЯТЬ МАРКЕРА ---
        self.last_rvec = None
        self.last_tvec = None
        self.is_tracking = False

        # Параметры игрового мира
        self.limit = 0.4  
        self.ball_pos = np.array([0.0, 0.0], dtype=np.float32)
        self.ball_vel = np.array([0.0, 0.0], dtype=np.float32)
        self.friction = 0.98

        # --- УЛУЧШЕННЫЕ СТЕНЫ (ЛАБИРИНТ) ---
        # Формат: [x_center, y_center, width, height]
        self.walls_3d = [
            [-0.38, 0.0, 0.04, 0.8],   # Внешняя левая
            [0.38, 0.0, 0.04, 0.8],    # Внешняя правая
            [0.0, -0.38, 0.8, 0.04],   # Внешняя нижняя
            [0.0, 0.38, 0.8, 0.04],    # Внешняя верхняя
            [-0.15, 0.15, 0.03, 0.3],  # Внутренняя перегородка 1
            [0.15, -0.15, 0.03, 0.3],  # Внутренняя перегородка 2
            [0.0, 0.0, 0.2, 0.03]      # Центральный блок
        ]

        self.COLORS = {'ball': (0, 255, 255), 'wall': (100, 50, 0), 'zone': (255, 0, 255)}

    def draw_3d_box(self, img, rvec, tvec, cam_mat, pos, size, color, h=-0.06):
        """Рисует объемный блок с тенями"""
        x, y = pos
        sw, sh = size[0]/2, size[1]/2
        pts_3d = np.float32([
            [x-sw, y-sh, 0], [x+sw, y-sh, 0], [x+sw, y+sh, 0], [x-sw, y+sh, 0],
            [x-sw, y-sh, h], [x+sw, y-sh, h], [x+sw, y+sh, h], [x-sw, y+sh, h]
        ])
        pts_2d, _ = cv2.projectPoints(pts_3d, rvec, tvec, cam_mat, None)
        pts_2d = np.int32(pts_2d).reshape(-1, 2)
        
        # Грани (объем)
        dark = (int(color[0]*0.6), int(color[1]*0.6), int(color[2]*0.6))
        for i in range(4):
            side = np.array([pts_2d[i], pts_2d[(i+1)%4], pts_2d[(i+1)%4+4], pts_2d[i+4]])
            cv2.fillPoly(img, [side], dark)
        # Крышка
        cv2.fillPoly(img, [pts_2d[4:]], color)
        cv2.polylines(img, [pts_2d[4:]], True, (255,255,255), 1)

    def process_frame(self, frame):
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        
        mask = np.zeros_like(frame)
        cam_mat = np.array([[w, 0, w/2], [0, w, h/2], [0, 0, 1]], dtype=np.float32)
        
        # Обновляем трекинг
        found_now = False
        if ids is not None and 0 in ids:
            idx = np.where(ids == 0)[0][0]
            m_s = 0.1
            obj_pts = np.float32([[-m_s/2, m_s/2, 0], [m_s/2, m_s/2, 0], 
                                  [m_s/2, -m_s/2, 0], [-m_s/2, -m_s/2, 0]])
            ret, rvec, tvec = cv2.solvePnP(obj_pts, corners[idx], cam_mat, None)
            if ret:
                self.last_rvec, self.last_tvec = rvec, tvec
                self.is_tracking = True
                found_now = True

        if self.is_tracking:
            rv, tv = self.last_rvec, self.last_tvec

            # --- ФИЗИКА ---
            self.ball_vel *= self.friction
            self.ball_pos += self.ball_vel
            
            # Коллизии со всеми стенами лабиринта
            for wx, wy, ww, wh in self.walls_3d:
                # Проверка вхождения мяча в прямоугольник стены
                if (wx - ww/2 < self.ball_pos[0] < wx + ww/2 and 
                    wy - wh/2 < self.ball_pos[1] < wy + wh/2):
                    
                    # Определяем с какой стороны удар (по X или по Y)
                    dx = abs(self.ball_pos[0] - wx) / ww
                    dy = abs(self.ball_pos[1] - wy) / wh
                    
                    if dx > dy:
                        self.ball_vel[0] *= -0.8
                        self.ball_pos[0] = wx + (ww/2 if self.ball_pos[0] > wx else -ww/2)
                    else:
                        self.ball_vel[1] *= -0.8
                        self.ball_pos[1] = wy + (wh/2 if self.ball_pos[1] > wy else -wh/2)

            # ВЗАИМОДЕЙСТВИЕ С РУЧКОЙ
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            p_mask = cv2.inRange(hsv, np.array([35, 60, 60]), np.array([85, 255, 255]))
            cnts, _ = cv2.findContours(p_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                c = max(cnts, key=cv2.contourArea)
                if cv2.contourArea(c) > 300:
                    M = cv2.moments(c)
                    px, py = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
                    ball_2d, _ = cv2.projectPoints(np.float32([[self.ball_pos[0], self.ball_pos[1], 0]]), rv, tv, cam_mat, None)
                    bx, by = ball_2d.ravel()
                    if math.hypot(px - bx, py - by) < 45:
                        self.ball_vel[0] = (bx - px) * 0.0005
                        self.ball_vel[1] = (by - py) * 0.0005

            # --- ОТРИСОВКА ---
            alpha = 0.4 if found_now else 0.2
            # Основание зоны
            self.draw_3d_box(mask, rv, tv, cam_mat, [0,0], [self.limit*2, self.limit*2], self.COLORS['zone'], h=0.005)
            # Все 3D стены
            for wall in self.walls_3d:
                self.draw_3d_box(mask, rv, tv, cam_mat, [wall[0], wall[1]], [wall[2], wall[3]], self.COLORS['wall'])
            # Мяч
            self.draw_3d_box(mask, rv, tv, cam_mat, self.ball_pos, [0.04, 0.04], self.COLORS['ball'], h=-0.04)

            # Возвращаем уже готовый обработанный кадр, а не одну маску
            return cv2.addWeighted(frame, 1.0, mask, alpha, 0)

        # Если маркера нет — просто возвращаем оригинальный кадр
        return frame


# Глобальный экземпляр и удобная функция-обертка,
# чтобы использовать этот модуль как остальные процессоры
engine = ARGame3D()

def process_ar_game(frame):
   
    return engine.process_frame(frame)