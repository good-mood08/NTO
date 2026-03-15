import cv2
import numpy as np
import math

class ARGameServer:
    def __init__(self):
        # Физика
        self.friction = 0.96
        self.pen_force = 5.0
        self.wall_bounce = 0.80
        self.ball_radius = 18
        self.finish_radius = 35

        # Настройка AprilTag
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16H5)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        self.game_zone = None  # (x1, y1, x2, y2)
        self.ball_pos = None  
        self.ball_vel = [0.0, 0.0]
        self.start_point = None
        self.finish_point = None
        self.walls = []

        self.COLORS = {
            'zone': (255, 0, 255), 
            'ball': (0, 255, 255),
            'pen': (0, 255, 0),
            'wall': (180, 120, 50),
            'start': (0, 255, 0),
            'finish': (0, 0, 255)
        }

        # Зеленая ручка
        self.lower_green = np.array([35, 60, 60])
        self.upper_green = np.array([85, 255, 255])

    def build_level(self, zone):
        zx1, zy1, zx2, zy2 = zone
        zw, zh = zx2 - zx1, zy2 - zy1
        
        self.start_point = (zx1 + int(zw * 0.1), zy2 - int(zh * 0.15))
        self.finish_point = (zx2 - int(zw * 0.1), zy1 + int(zh * 0.15))
        
        # Лабиринт
        self.walls = [
            (zx1 + int(zw * 0.35), zy1 + int(zh * 0.3), zx1 + int(zw * 0.45), zy2),
            (zx1 + int(zw * 0.65), zy1, zx1 + int(zw * 0.75), zy1 + int(zh * 0.7))
        ]

    def check_wall_collision(self):
        if not self.ball_pos: return
        for (wx1, wy1, wx2, wy2) in self.walls:
            cx = max(wx1, min(self.ball_pos[0], wx2))
            cy = max(wy1, min(self.ball_pos[1], wy2))
            dx, dy = self.ball_pos[0] - cx, self.ball_pos[1] - cy
            dist = math.hypot(dx, dy)

            if dist < self.ball_radius:
                if dist == 0: dist = 0.1 # Защита от деления на 0
                overlap = self.ball_radius - dist
                nx, ny = dx / dist, dy / dist
                
                # Выталкивание мяча
                self.ball_pos[0] += nx * overlap
                self.ball_pos[1] += ny * overlap
                
                # Отскок
                dot = self.ball_vel[0] * nx + self.ball_vel[1] * ny
                self.ball_vel[0] = (self.ball_vel[0] - 2 * dot * nx) * self.wall_bounce
                self.ball_vel[1] = (self.ball_vel[1] - 2 * dot * ny) * self.wall_bounce

    def process_frame(self, frame):
        # 1. Детекция зоны по маркерам
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        
        if ids is not None and len(ids) >= 2:
            m_pts = {idx[0]: np.mean(c[0], axis=0) for c, idx in zip(corners, ids)}
            if 0 in m_pts and 1 in m_pts:
                new_zone = (
                    int(min(m_pts[0][0], m_pts[1][0])), int(min(m_pts[0][1], m_pts[1][1])),
                    int(max(m_pts[0][0], m_pts[1][0])), int(max(m_pts[0][1], m_pts[1][1]))
                )
                # Перестраиваем уровень только если зона изменилась
                if self.game_zone != new_zone:
                    self.game_zone = new_zone
                    self.build_level(new_zone)
                    if self.ball_pos is None:
                        self.ball_pos = list(self.start_point)

        # 2. Поиск ручки
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        p_mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        cnts, _ = cv2.findContours(p_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pen_box = None
        
        if cnts:
            largest = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(largest) > 400:
                rect = cv2.minAreaRect(largest)
                pen_box = cv2.boxPoints(rect).astype(np.int32)
                pen_center = rect[0]

        # 3. Физика и логика игры
        if self.game_zone and self.ball_pos:
            zx1, zy1, zx2, zy2 = self.game_zone
            
            # Движение
            self.ball_vel[0] *= self.friction
            self.ball_vel[1] *= self.friction
            self.ball_pos[0] += self.ball_vel[0]
            self.ball_pos[1] += self.ball_vel[1]

            # Границы зоны (отскок)
            if self.ball_pos[0] <= zx1 + self.ball_radius or self.ball_pos[0] >= zx2 - self.ball_radius:
                self.ball_vel[0] *= -self.wall_bounce
                self.ball_pos[0] = np.clip(self.ball_pos[0], zx1 + self.ball_radius, zx2 - self.ball_radius)
            if self.ball_pos[1] <= zy1 + self.ball_radius or self.ball_pos[1] >= zy2 - self.ball_radius:
                self.ball_vel[1] *= -self.wall_bounce
                self.ball_pos[1] = np.clip(self.ball_pos[1], zy1 + self.ball_radius, zy2 - self.ball_radius)

            self.check_wall_collision()

            # Удар ручкой
            if pen_box is not None:
                dist_to_pen = cv2.pointPolygonTest(pen_box, (float(self.ball_pos[0]), float(self.ball_pos[1])), True)
                if dist_to_pen >= -self.ball_radius:
                    dx, dy = self.ball_pos[0] - pen_center[0], self.ball_pos[1] - pen_center[1]
                    d = math.hypot(dx, dy) or 1
                    self.ball_vel[0], self.ball_vel[1] = (dx/d) * self.pen_force, (dy/d) * self.pen_force

            # Проверка финиша
            if math.hypot(self.ball_pos[0] - self.finish_point[0], self.ball_pos[1] - self.finish_point[1]) < self.finish_radius:
                self.ball_pos = list(self.start_point)
                self.ball_vel = [0.0, 0.0]

            # 4. Отрисовка ПРЯМО НА FRAME
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), self.COLORS['zone'], 2)
            cv2.circle(frame, self.start_point, 20, self.COLORS['start'], 2)
            cv2.circle(frame, self.finish_point, self.finish_radius, self.COLORS['finish'], -1)
            
            for w in self.walls:
                cv2.rectangle(frame, (w[0], w[1]), (w[2], w[3]), self.COLORS['wall'], -1)
            
            cv2.circle(frame, (int(self.ball_pos[0]), int(self.ball_pos[1])), self.ball_radius, self.COLORS['ball'], -1)
            
            if pen_box is not None:
                cv2.drawContours(frame, [pen_box], 0, self.COLORS['pen'], 2)

        return frame

engine = ARGameServer()

def process_ar_game(frame):
    # Теперь функция возвращает модифицированный исходный кадр
    return engine.process_frame(frame)