"""
Snake LaboCita — Mini-jeu intégré à l'app FLA.
La nourriture forme le mot "LaboCita" en pixels.
Quand tout est mangé → popup victoire !
"""

SNAKE_GAME_HTML = """
<div id="snake-wrap" tabindex="0" style="
    outline:none; text-align:center; background:#0d1117;
    padding:15px; border-radius:12px; font-family:'Segoe UI',Tahoma,sans-serif;
">
    <div style="color:#26A69A; font-size:14px; margin-bottom:8px; letter-spacing:1px;">
        Score : <span id="sc">0</span> / <span id="tot">0</span>
    </div>
    <canvas id="snk" width="480" height="360" style="
        border:2px solid #00897B; border-radius:8px;
        box-shadow:0 0 25px rgba(0,137,123,0.3);
        display:block; margin:0 auto; cursor:pointer;
    "></canvas>
    <div id="snk-btns" style="margin-top:10px; user-select:none;">
        <div>
            <button onclick="snkDir(0,-1)" style="
                background:#1a2332; color:#26A69A; border:1px solid #00897B;
                border-radius:6px; width:44px; height:36px; font-size:18px; cursor:pointer;
            ">↑</button>
        </div>
        <div style="margin-top:4px;">
            <button onclick="snkDir(-1,0)" style="
                background:#1a2332; color:#26A69A; border:1px solid #00897B;
                border-radius:6px; width:44px; height:36px; font-size:18px; cursor:pointer; margin-right:4px;
            ">←</button>
            <button onclick="snkDir(0,1)" style="
                background:#1a2332; color:#26A69A; border:1px solid #00897B;
                border-radius:6px; width:44px; height:36px; font-size:18px; cursor:pointer; margin-right:4px;
            ">↓</button>
            <button onclick="snkDir(1,0)" style="
                background:#1a2332; color:#26A69A; border:1px solid #00897B;
                border-radius:6px; width:44px; height:36px; font-size:18px; cursor:pointer;
            ">→</button>
        </div>
        <div style="margin-top:6px;">
            <button id="snk-start-btn" onclick="snkStart()" style="
                background:#00897B; color:#fff; border:none;
                border-radius:6px; padding:6px 24px; font-size:13px; cursor:pointer;
            ">▶ Jouer</button>
        </div>
    </div>
    <div style="color:#555; font-size:11px; margin-top:8px;">
        Cliquez sur le jeu puis utilisez les flèches du clavier
    </div>
</div>

<script>
(function() {
    const cv = document.getElementById('snk');
    const ctx = cv.getContext('2d');
    const wrap = document.getElementById('snake-wrap');
    const COLS = 40, ROWS = 30, C = 12;

    // Police pixel 4x6 — lettres bien définies
    const FT = {
        'L': [
            [1,0,0,0],
            [1,0,0,0],
            [1,0,0,0],
            [1,0,0,0],
            [1,0,0,0],
            [1,1,1,1]
        ],
        'a': [
            [0,0,0,0],
            [0,0,0,0],
            [0,1,1,0],
            [1,0,0,1],
            [1,1,1,1],
            [1,0,0,1]
        ],
        'b': [
            [1,0,0,0],
            [1,0,0,0],
            [1,1,1,0],
            [1,0,0,1],
            [1,0,0,1],
            [1,1,1,0]
        ],
        'o': [
            [0,0,0,0],
            [0,0,0,0],
            [0,1,1,0],
            [1,0,0,1],
            [1,0,0,1],
            [0,1,1,0]
        ],
        'C': [
            [0,1,1,0],
            [1,0,0,1],
            [1,0,0,0],
            [1,0,0,0],
            [1,0,0,1],
            [0,1,1,0]
        ],
        'i': [
            [0,0,0,0],
            [0,1,0,0],
            [0,0,0,0],
            [0,1,0,0],
            [0,1,0,0],
            [0,1,0,0]
        ],
        't': [
            [0,0,0,0],
            [0,1,0,0],
            [1,1,1,0],
            [0,1,0,0],
            [0,1,0,0],
            [0,0,1,0]
        ]
    };

    function wordCells(w, sx, sy) {
        const cells = [];
        let ox = sx;
        for (const ch of w) {
            const bmp = FT[ch];
            if (!bmp) { ox += 5; continue; }
            for (let r = 0; r < bmp.length; r++)
                for (let c = 0; c < bmp[r].length; c++)
                    if (bmp[r][c]) cells.push({x: ox+c, y: sy+r});
            ox += 5;
        }
        return cells;
    }

    let snake, dir, ndir, food, score, over, won, on, spd, totalF;

    function init() {
        const letterW = 4, gap = 1, nLetters = 8;
        const ww = nLetters * letterW + (nLetters - 1) * gap;
        const sx = Math.floor((COLS - ww) / 2);
        const sy = Math.floor((ROWS - 6) / 2);
        food = wordCells("LaboCita", sx, sy);
        totalF = food.length;
        document.getElementById('tot').textContent = totalF;
        document.getElementById('sc').textContent = '0';
        snake = [{x:3, y:ROWS-3},{x:2, y:ROWS-3},{x:1, y:ROWS-3}];
        dir = {x:1, y:0}; ndir = {x:1, y:0};
        score = 0; over = false; won = false; on = false; spd = 105;
        document.getElementById('snk-start-btn').textContent = '▶ Jouer';
    }

    function draw() {
        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, cv.width, cv.height);

        // Grille subtile
        ctx.strokeStyle = '#111820';
        ctx.lineWidth = 0.3;
        for (let x = 0; x <= COLS; x++) {
            ctx.beginPath(); ctx.moveTo(x*C, 0); ctx.lineTo(x*C, ROWS*C); ctx.stroke();
        }
        for (let y = 0; y <= ROWS; y++) {
            ctx.beginPath(); ctx.moveTo(0, y*C); ctx.lineTo(COLS*C, y*C); ctx.stroke();
        }

        // Nourriture avec glow pulsé
        const pulse = 4 + Math.sin(Date.now() / 300) * 3;
        for (const f of food) {
            ctx.shadowColor = '#00897B';
            ctx.shadowBlur = pulse;
            ctx.fillStyle = '#b2dfdb';
            ctx.beginPath();
            ctx.arc(f.x*C + C/2, f.y*C + C/2, C/2 - 1.5, 0, Math.PI*2);
            ctx.fill();
            ctx.shadowBlur = 0;
        }

        // Corps du snake (dégradé queue → tête)
        for (let i = snake.length - 1; i >= 0; i--) {
            const s = snake[i];
            const t = i / Math.max(snake.length - 1, 1);
            if (i === 0) {
                ctx.fillStyle = '#00897B';
                ctx.shadowColor = '#00897B';
                ctx.shadowBlur = 6;
            } else {
                const r = Math.round(38 + (1-t) * (13-38));
                const g = Math.round(166 + (1-t) * (30-166));
                const b2 = Math.round(154 + (1-t) * (40-154));
                ctx.fillStyle = 'rgb('+r+','+g+','+b2+')';
                ctx.shadowBlur = 0;
            }
            const pad = i === 0 ? 0.5 : 1;
            ctx.beginPath();
            ctx.roundRect(s.x*C+pad, s.y*C+pad, C-pad*2, C-pad*2, 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        }

        // Yeux
        if (snake.length > 0) {
            const h = snake[0];
            ctx.fillStyle = '#e0f2f1';
            let ex1, ey1, ex2, ey2;
            if (dir.x===1)       { ex1=ex2=h.x*C+C-3; ey1=h.y*C+3; ey2=h.y*C+C-3; }
            else if (dir.x===-1) { ex1=ex2=h.x*C+3;   ey1=h.y*C+3; ey2=h.y*C+C-3; }
            else if (dir.y===-1) { ey1=ey2=h.y*C+3;   ex1=h.x*C+3; ex2=h.x*C+C-3; }
            else                 { ey1=ey2=h.y*C+C-3;  ex1=h.x*C+3; ex2=h.x*C+C-3; }
            ctx.beginPath(); ctx.arc(ex1,ey1,1.5,0,Math.PI*2); ctx.fill();
            ctx.beginPath(); ctx.arc(ex2,ey2,1.5,0,Math.PI*2); ctx.fill();
        }

        ctx.textAlign = 'center';

        // Écran de démarrage
        if (!on && !over && !won) {
            ctx.fillStyle = 'rgba(13,17,23,0.75)';
            ctx.fillRect(0, 0, cv.width, cv.height);
            ctx.fillStyle = '#26A69A';
            ctx.font = 'bold 22px Segoe UI';
            ctx.fillText('🐍 Snake LaboCita', cv.width/2, cv.height/2 - 15);
            ctx.fillStyle = '#888';
            ctx.font = '13px Segoe UI';
            ctx.fillText('Appuyez sur ESPACE ou ▶ Jouer', cv.width/2, cv.height/2 + 15);
        }

        // Game Over
        if (over && !won) {
            ctx.fillStyle = 'rgba(13,17,23,0.8)';
            ctx.fillRect(0, 0, cv.width, cv.height);
            ctx.fillStyle = '#e94560';
            ctx.font = 'bold 22px Segoe UI';
            ctx.fillText('Game Over !', cv.width/2, cv.height/2 - 12);
            ctx.fillStyle = '#888';
            ctx.font = '13px Segoe UI';
            ctx.fillText('Score : ' + score + ' / ' + totalF, cv.width/2, cv.height/2 + 12);
            ctx.fillText('ESPACE ou ▶ pour rejouer', cv.width/2, cv.height/2 + 35);
        }

        // Victoire !
        if (won) {
            ctx.fillStyle = 'rgba(13,17,23,0.88)';
            ctx.fillRect(0, 0, cv.width, cv.height);

            // Sigle LaboCita (cercle teal avec L)
            const cx = cv.width/2, cy = cv.height/2 - 45;
            ctx.shadowColor = '#00897B';
            ctx.shadowBlur = 20;
            ctx.beginPath();
            ctx.arc(cx, cy, 28, 0, Math.PI*2);
            ctx.fillStyle = '#00897B';
            ctx.fill();
            ctx.shadowBlur = 0;
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 26px Segoe UI';
            ctx.fillText('🧪', cx, cy + 9);

            // Texte principal doré
            ctx.shadowColor = '#ffb74d';
            ctx.shadowBlur = 25;
            ctx.fillStyle = '#ffb74d';
            ctx.font = 'bold 24px Segoe UI';
            ctx.fillText('🏆  Vous êtes le meilleur !  🏆', cx, cy + 55);
            ctx.shadowBlur = 0;

            // LaboCita Validé
            ctx.fillStyle = '#26A69A';
            ctx.font = 'bold 18px Segoe UI';
            ctx.fillText('LaboCita  ✅  Validé', cx, cy + 85);

            // Score
            ctx.fillStyle = '#888';
            ctx.font = '13px Segoe UI';
            ctx.fillText('Score parfait : ' + totalF + ' / ' + totalF, cx, cy + 110);
            ctx.font = '11px Segoe UI';
            ctx.fillText('ESPACE ou ▶ pour rejouer', cx, cy + 130);
        }
    }

    function update() {
        if (!on || over || won) return;
        dir = ndir;
        const nh = {x: snake[0].x + dir.x, y: snake[0].y + dir.y};
        if (nh.x < 0 || nh.x >= COLS || nh.y < 0 || nh.y >= ROWS) { over = true; return; }
        for (const s of snake) if (s.x === nh.x && s.y === nh.y) { over = true; return; }
        snake.unshift(nh);
        const fi = food.findIndex(f => f.x === nh.x && f.y === nh.y);
        if (fi !== -1) {
            food.splice(fi, 1);
            score++;
            document.getElementById('sc').textContent = score;
            if (food.length === 0) won = true;
            if (spd > 55) spd -= 1;
        } else {
            snake.pop();
        }
    }

    let lt = 0;
    function loop(ts) {
        if (ts - lt >= spd) { update(); lt = ts; }
        draw();
        requestAnimationFrame(loop);
    }

    wrap.addEventListener('keydown', function(e) {
        if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '].includes(e.key)) e.preventDefault();
        if (e.key === ' ') { snkStart(); return; }
        if (!on) return;
        switch(e.key) {
            case 'ArrowUp':    if (dir.y!==1)  ndir={x:0,y:-1}; break;
            case 'ArrowDown':  if (dir.y!==-1) ndir={x:0,y:1};  break;
            case 'ArrowLeft':  if (dir.x!==1)  ndir={x:-1,y:0}; break;
            case 'ArrowRight': if (dir.x!==-1) ndir={x:1,y:0};  break;
        }
    });

    cv.addEventListener('click', function() { wrap.focus(); });

    window.snkDir = function(dx, dy) {
        if (!on) return;
        if (dx === -dir.x && dy === 0) return;
        if (dy === -dir.y && dx === 0) return;
        ndir = {x: dx, y: dy};
    };

    window.snkStart = function() {
        if (!on || over || won) {
            init();
            on = true;
            document.getElementById('snk-start-btn').textContent = '🔄 Rejouer';
            wrap.focus();
        }
    };

    init();
    requestAnimationFrame(loop);
    setTimeout(function() { wrap.focus(); }, 100);
})();
</script>
"""
