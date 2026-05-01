import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
import numpy as np
import math

class MasterMaze:
    def __init__(self, width, height):
        self.width = int(width)
        self.height = int(height)
        self.grid = {}
        for x in range(self.width):
            for y in range(self.height):
                self.grid[(x, y)] = {'right': False, 'top': False}
        self.entrance_side = None
        self.entrance_pos = None

    def generate_maze(self):
        stack = [(0, 0)]
        visited = {(0, 0)}
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            if cx + 1 < self.width and (cx + 1, cy) not in visited: neighbors.append(((cx + 1, cy), 'right'))
            if cy + 1 < self.height and (cx, cy + 1) not in visited: neighbors.append(((cx, cy + 1), 'top'))
            if cx - 1 >= 0 and (cx - 1, cy) not in visited: neighbors.append(((cx - 1, cy), 'left'))
            if cy - 1 >= 0 and (cx, cy - 1) not in visited: neighbors.append(((cx, cy - 1), 'bottom'))
            if neighbors:
                (nx, ny), direction = random.choice(neighbors)
                if direction == 'right': self.grid[(cx, cy)]['right'] = True
                elif direction == 'top': self.grid[(cx, cy)]['top'] = True
                elif direction == 'left': self.grid[(nx, ny)]['right'] = True
                elif direction == 'bottom': self.grid[(nx, ny)]['top'] = True
                visited.add((nx, ny))
                stack.append((nx, ny))
            else:
                stack.pop()

    def add_route_choices(self, variety=0.15):
        removable = []
        for x in range(self.width):
            for y in range(self.height):
                if x < self.width - 1 and not self.grid[(x, y)]['right']: removable.append(((x, y), 'right'))
                if y < self.height - 1 and not self.grid[(x, y)]['top']: removable.append(((x, y), 'top'))
        count = min(int(len(removable) * variety), len(removable) // 3)
        if count == 0: return
        for (x, y), d in random.sample(removable, count):
            self.grid[(x, y)][d] = True

    def create_entrance(self):
        sides = ['bottom', 'top', 'left', 'right']
        self.entrance_side = random.choice(sides)
        if self.entrance_side in ['bottom', 'top']:
            self.entrance_pos = random.randint(max(1, self.width//4), min(self.width-2, 3*self.width//4))
        else:
            self.entrance_pos = random.randint(max(1, self.height//4), min(self.height-2, 3*self.height//4))

    def enforce_constraints(self):
        max_h, max_v = self.width - 1, self.height - 1
        for y in range(self.height - 1):
            clen, sx = 0, 0
            for x in range(self.width):
                if not self.grid[(x, y)]['top']: clen += 1
                else:
                    if clen > max_h: self.grid[(random.randint(sx, x-1), y)]['top'] = True
                    clen, sx = 0, x+1
            if clen > max_h: self.grid[(random.randint(sx, self.width-1), y)]['top'] = True

        for x in range(self.width - 1):
            clen, sy = 0, 0
            for y in range(self.height):
                if not self.grid[(x, y)]['right']: clen += 1
                else:
                    if clen > max_v: self.grid[(x, random.randint(sy, y-1))]['right'] = True
                    clen, sy = 0, y+1
            if clen > max_v: self.grid[(x, random.randint(sy, self.height-1))]['right'] = True

    def _is_valid_vertex(self, px, py):
        if px <= 0 or px >= self.width or py <= 0 or py >= self.height: return False
        wl = not self.grid[(px-1, py-1)]['top']
        wr = not self.grid[(px, py-1)]['top']
        wu = not self.grid[(px-1, py-1)]['right']
        wd = not self.grid[(px-1, py)]['right']
        cnt = wl + wr + wu + wd
        return cnt > 0 and not (cnt == 2 and ((wl and wr) or (wu and wd)))

    def _get_fresh_valid_corners(self):
        return [(x, y) for x in range(1, self.width) for y in range(1, self.height) if self._is_valid_vertex(x, y)]

    def _get_safe_shift(self, px, py):
        dx, dy, p = 0.0, 0.0, 1.0
        try:
            if not self.grid[(px-1, py)]['right']: dy -= p
            if not self.grid[(px-1, py-1)]['right']: dy += p
            if not self.grid[(px, py-1)]['top']: dx -= p
            if not self.grid[(px-1, py-1)]['top']: dx += p
        except KeyError: pass
        if px == 0: dx += p
        if px == self.width: dx -= p
        if py == 0: dy += p
        if py == self.height: dy -= p
        l = math.hypot(dx, dy)
        return (px + (dx/l)*0.25, py + (dy/l)*0.25) if l > 0 else (px, py)

    def _get_zone_3x3(self, x, y):
        return min(2, int(x / (self.width / 3))) + min(2, int(y / (self.height / 3))) * 3

    # ==========================================
    # ИЗМЕНЕНИЕ 1: Уменьшена доля центра в пуле
    # ==========================================
    def generate_cp_pool(self, total_cps):
        corners = self._get_fresh_valid_corners()
        random.shuffle(corners)
        center_cps = [p for p in corners if self._get_zone_3x3(*p) == 4]
        outer_cps = [p for p in corners if self._get_zone_3x3(*p) != 4]
        
        # Было 0.4 (40%), стало 0.25 (25%). Больше точек по краям!
        center_count = max(int(total_cps * 0.25), 2)
        return center_cps[:center_count] + outer_cps[:total_cps - center_count]

    def generate_course(self, pool, start, finish, target_len, course_idx, total_courses):
        difficulty = course_idx / max(1, total_courses - 1)
        map_diag = math.hypot(self.width, self.height)
        
        if difficulty < 0.3:
            max_leg_dist = map_diag * 0.35
            prefer_short = True
            max_center_repeats = 0
        elif difficulty < 0.7:
            max_leg_dist = map_diag * 0.6
            prefer_short = False
            max_center_repeats = 3
        else:
            max_leg_dist = map_diag * 0.9
            prefer_short = False
            max_center_repeats = 6

        route = [start]
        current = start
        used_counts = {p: 0 for p in pool}

        for _ in range(target_len):
            # ==========================================
            # ИЗМЕНЕНИЕ 2: Поиск пустых зон
            # ==========================================
            zones = [0] * 9
            for p in route: zones[self._get_zone_3x3(*p)] += 1
            
            # Находим зоны, где меньше всего пунктов (приоритет заполнения)
            min_visits = min(zones)
            target_zones = [z for z, count in enumerate(zones) if count == min_visits]

            candidates = []
            for p in pool:
                if p == current: continue
                zone = self._get_zone_3x3(*p)
                is_center = (zone == 4)
                count = used_counts.get(p, 0)
                
                if is_center and count >= max_center_repeats: continue
                if not is_center and count >= 1: continue
                if p[0] == current[0] or p[1] == current[1]: continue
                
                dist = math.hypot(p[0]-current[0], p[1]-current[1])
                if difficulty < 0.3 and dist > max_leg_dist: continue

                # Логика приоритетов
                pri = 0
                if count == 0: pri += 2  # Бонус за первый визит
                
                # ГИГАНТСКИЙ бонус, если точка находится в "пустой" зоне
                if zone in target_zones: pri += 5 

                dist_score = -dist if prefer_short else dist
                candidates.append({'p': p, 'pri': pri, 'dist_score': dist_score})

            if not candidates:
                max_leg_dist += 1.0
                continue

            candidates.sort(key=lambda k: (k['pri'], k['dist_score']), reverse=True)
            chosen = random.choice(candidates[:min(3, len(candidates))])['p']
            
            route.append(chosen)
            used_counts[chosen] += 1
            current = chosen

        route.append(finish)
        return route

    def _get_optimal_text_pos(self, cx, cy, vx, vy, all_centers, adjacents, label=""):
        dirs = [(1, 1), (-1, 1), (-1, -1), (1, -1), (0, 1), (0, -1), (1, 0), (-1, 0)]
        best_pos = (cx + 0.7, cy + 0.7)
        best_score = -1000000
        
        label_len = len(label)
        text_dist = 0.60 + 0.04 * max(0, label_len - 1)
        safe_radius_other = 0.45 + 0.04 * max(0, label_len - 1)
        
        norm_vecs = []
        for ax, ay in adjacents:
            l = math.hypot(ax - cx, ay - cy)
            if l > 0.01: norm_vecs.append(((ax - cx)/l, (ay - cy)/l))

        def is_quadrant_blocked(q_dx, q_dy):
            try:
                if q_dx > 0:
                    if q_dy > 0: 
                         if not self.grid[(vx-1, vy-1)]['right']: return True 
                         if not self.grid[(vx, vy-1)]['top']: return True    
                    else:          
                         if not self.grid[(vx-1, vy)]['right']: return True  
                         if not self.grid[(vx, vy-1)]['top']: return True    
                else: 
                    if q_dy > 0: 
                         if not self.grid[(vx-1, vy-1)]['right']: return True 
                         if not self.grid[(vx-1, vy-1)]['top']: return True   
                    else:          
                         if not self.grid[(vx-1, vy)]['right']: return True  
                         if not self.grid[(vx-1, vy-1)]['top']: return True  
            except KeyError: pass
            return False

        for dx, dy in dirs:
            mag = math.hypot(dx, dy)
            ndx, ndy = dx/mag, dy/mag
            score = 0
            tx, ty = cx + ndx * text_dist, cy + ndy * text_dist

            if tx < -0.5 or tx > self.width + 0.5 or ty < -0.5 or ty > self.height + 0.8:
                score -= 5000
            
            is_blocked = False
            if dx != 0 and dy != 0: 
                if is_quadrant_blocked(dx, dy): is_blocked = True
            else: 
                if dx == 1 and is_quadrant_blocked(1, 1) and is_quadrant_blocked(1, -1): is_blocked = True
                elif dx == -1 and is_quadrant_blocked(-1, 1) and is_quadrant_blocked(-1, -1): is_blocked = True
                elif dy == 1 and is_quadrant_blocked(1, 1) and is_quadrant_blocked(-1, 1): is_blocked = True
                elif dy == -1 and is_quadrant_blocked(1, -1) and is_quadrant_blocked(-1, -1): is_blocked = True
            if is_blocked: score -= 2000
            
            for nlx, nly in norm_vecs:
                if ndx * nlx + ndy * nly > 0.85: score -= 800
            
            for ox, oy in all_centers:
                if abs(ox - cx) < 0.01 and abs(oy - cy) < 0.01: continue
                if math.hypot(tx - ox, ty - oy) < safe_radius_other:
                    score -= 3000 
            
            if score > best_score:
                best_score = score
                best_pos = (tx, ty)
                
        best_pos = (max(-0.8, min(self.width + 0.8, best_pos[0])),
                    max(-0.8, min(self.height + 1.0, best_pos[1])))
        return best_pos

    def _get_construction_points(self):
        points = set()
        for x in range(self.width + 1):
            points.add((x, 0))
            points.add((x, self.height))
        for y in range(1, self.height):
            points.add((0, y))
            points.add((self.width, y))
        for x in range(self.width):
            for y in range(self.height):
                if not self.grid[(x, y)]['right']: 
                    points.add((x + 1, y))
                    points.add((x + 1, y + 1))
                if not self.grid[(x, y)]['top']: 
                    points.add((x, y + 1))
                    points.add((x + 1, y + 1))
        return points

    def draw_map(self, filename, course_points, title="", draw_lines=True, is_master=False):
        ar = self.width / self.height
        base_w, base_h = 8.27, 5.83
        if ar > 1: fw, fh = base_w, base_w / ar
        else:      fh, fw = base_h, base_h * ar
            
        fig = plt.figure(figsize=(fw, fh))
        ax = fig.add_subplot(111)
        
        ax.set_xlim(-1.2, self.width + 1.2)
        ax.set_ylim(-1.2, self.height + 1.4) 
        ax.set_aspect('equal', adjustable='box')
        ax.axis('off')
        ax.text(self.width/2, self.height + 0.4, title, ha='center', va='bottom', fontsize=14, fontweight='bold', color='#111')

        ww, cw_std, cw_thin, sw = 2.4, 1.8, 1.2, 1.2
        col_w, col_c = 'black', '#E6007E'
        
        if is_master:
            for vx, vy in self._get_construction_points():
                ax.add_patch(patches.Circle((vx, vy), 0.07, facecolor='black', edgecolor='none', zorder=1))

        if self.entrance_side == 'bottom':
            ax.plot([0, self.entrance_pos], [0, 0], color=col_w, lw=ww, zorder=2)
            ax.plot([self.entrance_pos + 1, self.width], [0, 0], color=col_w, lw=ww, zorder=2)
        elif self.entrance_side == 'top':
            ax.plot([0, self.entrance_pos], [self.height, self.height], color=col_w, lw=ww, zorder=2)
            ax.plot([self.entrance_pos + 1, self.width], [self.height, self.height], color=col_w, lw=ww, zorder=2)
        elif self.entrance_side == 'left':
            ax.plot([0, 0], [0, self.entrance_pos], color=col_w, lw=ww, zorder=2)
            ax.plot([0, 0], [self.entrance_pos + 1, self.height], color=col_w, lw=ww, zorder=2)
        elif self.entrance_side == 'right':
            ax.plot([self.width, self.width], [0, self.entrance_pos], color=col_w, lw=ww, zorder=2)
            ax.plot([self.width, self.width], [self.entrance_pos + 1, self.height], color=col_w, lw=ww, zorder=2)

        if self.entrance_side != 'bottom': ax.plot([0, self.width], [0, 0], color=col_w, lw=ww, zorder=2)
        if self.entrance_side != 'top':    ax.plot([0, self.width], [self.height, self.height], color=col_w, lw=ww, zorder=2)
        if self.entrance_side != 'left':   ax.plot([0, 0], [0, self.height], color=col_w, lw=ww, zorder=2)
        if self.entrance_side != 'right':  ax.plot([self.width, self.width], [0, self.height], color=col_w, lw=ww, zorder=2)

        for x in range(self.width):
            for y in range(self.height):
                if not self.grid[(x, y)]['right'] and x < self.width - 1:
                    ax.plot([x + 1, x + 1], [y, y + 1], color=col_w, lw=ww, zorder=2)
                if not self.grid[(x, y)]['top'] and y < self.height - 1:
                    ax.plot([x, x + 1], [y + 1, y + 1], color=col_w, lw=ww, zorder=2)

        if len(course_points) > 1:
            full_shifted = [self._get_safe_shift(c[0], c[1]) for c in course_points]
            
            cp_indices_map = {}
            for idx, coord in enumerate(course_points):
                if 0 < idx < len(course_points) - 1:
                    cp_indices_map.setdefault(coord, []).append(idx)
            
            unique_cp_coords = list(cp_indices_map.keys())
            unique_shifted = [self._get_safe_shift(c[0], c[1]) for c in unique_cp_coords]
            coord_to_shifted = dict(zip(unique_cp_coords, unique_shifted))
            
            cp_count = len(course_points)
            current_lw = cw_thin if cp_count > 12 else cw_std
            
            if draw_lines:
                for i in range(len(full_shifted) - 1):
                    p1, p2 = full_shifted[i], full_shifted[i+1]
                    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
                    d = math.hypot(dx, dy)
                    if d > 0.75:
                        nx, ny = dx/d, dy/d
                        ax.plot([p1[0]+nx*0.35, p2[0]-nx*0.35], 
                                [p1[1]+ny*0.35, p2[1]-ny*0.35], 
                                color=col_c, lw=current_lw, solid_capstyle='round', zorder=3)

            px, py = full_shifted[0]
            ang = np.arctan2(full_shifted[1][1]-py, full_shifted[1][0]-px)
            sz = 0.45
            tri = patches.Polygon([(px+sz*np.cos(ang), py+sz*np.sin(ang)),
                                   (px+sz*np.cos(ang+2.5), py+sz*np.sin(ang+2.5)),
                                   (px+sz*np.cos(ang-2.5), py+sz*np.sin(ang-2.5))],
                                  closed=True, edgecolor=col_c, facecolor='none', lw=sw, zorder=4)
            ax.add_patch(tri)

            px, py = full_shifted[-1]
            ax.add_patch(patches.Circle((px, py), 0.35, edgecolor=col_c, facecolor='none', lw=sw, zorder=4))
            ax.add_patch(patches.Circle((px, py), 0.26, edgecolor=col_c, facecolor='none', lw=sw, zorder=4))

            for coord, indices in cp_indices_map.items():
                px, py = coord_to_shifted[coord]
                label = "/".join(map(str, indices))
                
                adjacents = []
                for idx in indices:
                    if idx > 0: adjacents.append(full_shifted[idx-1])
                    if idx < len(full_shifted)-1: adjacents.append(full_shifted[idx+1])
                adjacents = list(set(map(tuple, adjacents)))

                tx, ty = self._get_optimal_text_pos(px, py, coord[0], coord[1], unique_shifted, adjacents, label)
                
                ax.add_patch(patches.Circle((px, py), 0.35, edgecolor=col_c, facecolor='none', lw=sw, zorder=4))
                ax.text(tx, ty, label, color=col_c, fontsize=11, ha='center', va='center', 
                        fontweight='bold', zorder=5, clip_on=False,
                        bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=0.1))

        plt.savefig(filename, format='png' if hasattr(filename, 'read') else 'pdf', bbox_inches='tight', pad_inches=0.3)
        plt.close()

if __name__ == "__main__":
    print("=" * 60)
    print("       🌀 МАСТЕР ЛАБИРИНТ (Full Coverage) 🌀")
    print("=" * 60)
    try:
        w = int(input("\n📏 Ширина (5-50): "))
        h = int(input("📏 Высота (5-50): "))
        cp_total = int(input("🚩 Уникальных точек в пуле КП: "))
        num_c = int(input("🔢 Количество дистанций: "))
        
        maze = MasterMaze(w, h)
        print("\n⏳ Генерация геометрии лабиринта...")
        maze.generate_maze()
        maze.add_route_choices(variety=0.15)
        maze.enforce_constraints()
        maze.create_entrance()
        
        print("🗺️ 1/3 Создание пула координат (Больше точек по краям)...")
        cp_pool = maze.generate_cp_pool(cp_total)
        
        print("🗺️ 2/3 Генерация дистанций...\n")
        start_coord = (maze.entrance_pos, 0) if maze.entrance_side == 'bottom' else \
                      (maze.entrance_pos, h) if maze.entrance_side == 'top' else \
                      (0, maze.entrance_pos) if maze.entrance_side == 'left' else (w, maze.entrance_pos)
        finish_coord = (maze.entrance_pos + 1, 0) if maze.entrance_side == 'bottom' else \
                       (maze.entrance_pos + 1, h) if maze.entrance_side == 'top' else \
                       (0, maze.entrance_pos + 1) if maze.entrance_side == 'left' else (w, maze.entrance_pos + 1)

        for i in range(num_c):
            ratio = 0.4 + 0.6 * (i / max(1, num_c - 1))
            target_len = max(3, int(cp_total * ratio))
            path = maze.generate_course(cp_pool, start_coord, finish_coord, target_len, i, num_c)
            
            fname = f"Maze_Course_{i+1}.pdf"
            maze.draw_map(fname, path, title=f"ДИСТАНЦИЯ {i+1}", draw_lines=True, is_master=False)
            print(f"✅ {fname} ({len(path)-2} шагов)")
            
        print("\n🗺️ 3/3 Отрисовка Мастер-карты...")
        master_path = [start_coord] + cp_pool + [finish_coord]
        maze.draw_map("Maze_Master.pdf", master_path, title="МАСТЕР-КАРТА", draw_lines=False, is_master=True)
        print(f"✅ Maze_Master.pdf (Все точки пула + разметка)\n🎉 Готово!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()