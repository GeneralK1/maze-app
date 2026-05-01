import os
import io
import base64
import zipfile
from flask import Flask, request, send_file, jsonify, render_template_string
from flask_cors import CORS
from master_maze import MasterMaze

app = Flask(__name__, static_folder='static')
CORS(app)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мастер Лабиринт</title>
    <style>
        body { font-family: sans-serif; padding: 20px; text-align: center; background: #f0f2f5; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }
        input { width: 100%; padding: 10px; margin: 5px 0 15px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #0077FF; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; margin: 5px 0; }
        button:disabled { background: #ccc; }
        #status { margin-top: 15px; color: #333; }
        #preview-container { margin-top: 15px; display: none; }
        #preview-img { max-width: 100%; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🌀 Мастер Лабиринт</h2>
        <input type="number" id="w" value="20" placeholder="Ширина">
        <input type="number" id="h" value="20" placeholder="Высота">
        <input type="number" id="cp" value="15" placeholder="КП">
        <input type="number" id="courses" value="3" placeholder="Дистанций">
        <button id="btn-preview" onclick="showPreview()">🔍 Предпросмотр</button>
        <button id="btn-download" style="display:none;" onclick="downloadZip()">📥 Скачать ZIP</button>
        <div id="status"></div>
        <div id="preview-container"><img id="preview-img"></div>
    </div>
    <script>
        async function showPreview() {
            const btnP = document.getElementById('btn-preview');
            const btnD = document.getElementById('btn-download');
            const status = document.getElementById('status');
            btnP.disabled = true; status.textContent = '⏳ Генерация...';
            try {
                const res = await fetch('/preview', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({w: +document.getElementById('w').value, h: +document.getElementById('h').value, cp: +document.getElementById('cp').value})
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('preview-img').src = data.image;
                    document.getElementById('preview-container').style.display = 'block';
                    btnD.style.display = 'block'; status.textContent = '✅ Готово!';
                } else status.textContent = '❌ ' + data.error;
            } catch(e) { status.textContent = '❌ Ошибка'; }
            finally { btnP.disabled = false; }
        }
        async function downloadZip() {
            const btnD = document.getElementById('btn-download');
            btnD.disabled = true; document.getElementById('status').textContent = '⏳ Подготовка ZIP...';
            try {
                const res = await fetch('/generate', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({w: +document.getElementById('w').value, h: +document.getElementById('h').value, cp: +document.getElementById('cp').value, courses: +document.getElementById('courses').value})
                });
                if(!res.ok) throw new Error('Ошибка');
                const blob = await res.blob(); const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url; a.download = 'Maze_Set.zip'; a.click();
                document.getElementById('status').textContent = '✅ Скачивание начато!';
            } catch(e) { document.getElementById('status').textContent = '❌ Ошибка скачивания'; }
            finally { btnD.disabled = false; }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    if os.path.exists('static/index.html'):
        return app.send_static_file('index.html')
    return render_template_string(HTML_TEMPLATE)

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
        # Мастер-карта: показываем ВСЕ столбы (pole_coords=cp_pool)
        maze.draw_map(img_buffer, master_path, title="ПРЕДПРОСМОТР", draw_lines=False, is_master=True, pole_coords=cp_pool)
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
                
                # Дистанция: показываем столбы ТОЛЬКО для используемых КП (pole_coords=path[1:-1])
                img_data = io.BytesIO()
                maze.draw_map(img_data, path, title=f"ДИСТАНЦИЯ {i+1}", draw_lines=True, is_master=False, pole_coords=path[1:-1])
                zf.writestr(f"Maze_Course_{i+1}.pdf", img_data.getvalue())

            master_path = [start_coord] + cp_pool + [finish_coord]
            img_data = io.BytesIO()
            # Мастер-карта: ВСЕ столбы
            maze.draw_map(img_data, master_path, title="МАСТЕР-КАРТА", draw_lines=False, is_master=True, pole_coords=cp_pool)
            zf.writestr("Maze_Master.pdf", img_data.getvalue())

        memory_file.seek(0)
        return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name=f"Maze_{w}x{h}.zip")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)