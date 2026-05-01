import os
import io
import base64
import zipfile
from flask import Flask, request, send_file, jsonify, render_template_string
from flask_cors import CORS
from master_maze import MasterMaze

app = Flask(__name__, static_folder='static')
CORS(app)

@app.route('/preview', methods=['POST'])
def preview():
    try:
        data = request.json
        w, h, cp_total = int(data['w']), int(data['h']), int(data['cp'])
        maze = MasterMaze(w, h)
        maze.generate_maze()
        maze.add_route_choices(variety=0.15)
        maze.enforce_constraints()
        maze.create_entrance()
        
        start_coord = (maze.entrance_pos, 0) if maze.entrance_side == 'bottom' else \
                      (maze.entrance_pos, h) if maze.entrance_side == 'top' else \
                      (0, maze.entrance_pos) if maze.entrance_side == 'left' else (w, maze.entrance_pos)
        finish_coord = (maze.entrance_pos + 1, 0) if maze.entrance_side == 'bottom' else \
                       (maze.entrance_pos + 1, h) if maze.entrance_side == 'top' else \
                       (0, maze.entrance_pos + 1) if maze.entrance_side == 'left' else (w, maze.entrance_pos + 1)

        cp_pool = maze.generate_cp_pool(cp_total)
        master_path = [start_coord] + cp_pool + [finish_coord]

        img_buffer = io.BytesIO()
        # 🔧 Генерируем PNG для быстрого отображения
        maze.draw_map(img_buffer, master_path, title="ПРЕДПРОСМОТР", draw_lines=False, is_master=True, pole_coords=cp_pool, img_format='png')
        img_buffer.seek(0)
        return jsonify({"success": True, "image": f"data:image/png;base64,{base64.b64encode(img_buffer.read()).decode('utf-8')}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        w, h, cp_total, num_c = int(data['w']), int(data['h']), int(data['cp']), int(data['courses'])
        maze = MasterMaze(w, h)
        maze.generate_maze()
        maze.add_route_choices(variety=0.15)
        maze.enforce_constraints()
        maze.create_entrance()
        
        start_coord = (maze.entrance_pos, 0) if maze.entrance_side == 'bottom' else \
                      (maze.entrance_pos, h) if maze.entrance_side == 'top' else \
                      (0, maze.entrance_pos) if maze.entrance_side == 'left' else (w, maze.entrance_pos)
        finish_coord = (maze.entrance_pos + 1, 0) if maze.entrance_side == 'bottom' else \
                       (maze.entrance_pos + 1, h) if maze.entrance_side == 'top' else \
                       (0, maze.entrance_pos + 1) if maze.entrance_side == 'left' else (w, maze.entrance_pos + 1)

        cp_pool = maze.generate_cp_pool(cp_total)
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i in range(num_c):
                ratio = 0.4 + 0.6 * (i / max(1, num_c - 1))
                target_len = max(3, int(cp_total * ratio))
                path = maze.generate_course(cp_pool, start_coord, finish_coord, target_len, i, num_c)
                
                # 🔧 Генерируем PDF для печати
                img_data = io.BytesIO()
                maze.draw_map(img_data, path, title=f"ДИСТАНЦИЯ {i+1}", draw_lines=True, is_master=False, pole_coords=path[1:-1], img_format='pdf')
                zf.writestr(f"Maze_Course_{i+1}.pdf", img_data.getvalue())

            master_path = [start_coord] + cp_pool + [finish_coord]
            img_data = io.BytesIO()
            maze.draw_map(img_data, master_path, title="МАСТЕР-КАРТА", draw_lines=False, is_master=True, pole_coords=cp_pool, img_format='pdf')
            zf.writestr("Maze_Master.pdf", img_data.getvalue())

        memory_file.seek(0)
        return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name=f"Maze_{w}x{h}.zip")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    if os.path.exists('static/index.html'):
        return app.send_static_file('index.html')
    return "Файл интерфейса не найден. Проверьте папку static/index.html"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)