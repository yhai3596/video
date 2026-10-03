<!doctype html>
<!-- 模板：由 tools/narrate.py 生成 index.html，不要直接改 index.html -->
<html lang="zh-CN" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <!-- GSAP 本地化：渲染用的 Chromium 不走代理，CDN 会加载失败 -->
    <script src="assets/gsap.min.js"></script>
    <style>
      @font-face {
        font-family: "CJK";
        src: local("Noto Sans CJK SC");
        font-weight: 400;
      }
      @font-face {
        font-family: "CJK";
        src: local("Noto Sans CJK SC Bold");
        font-weight: 700;
      }
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      html,
      body {
        width: 1920px;
        height: 1080px;
        overflow: hidden;
        background: #0b1220;
      }
      #root {
        position: relative;
        width: 100%;
        height: 100%;
        font-family: "CJK", sans-serif;
        color: #e6edf7;
        /* 工程蓝图网格 */
        background-color: #0b1220;
        background-image:
          linear-gradient(rgba(90, 140, 220, 0.08) 1px, transparent 1px),
          linear-gradient(90deg, rgba(90, 140, 220, 0.08) 1px, transparent 1px);
        background-size: 60px 60px;
      }
      .clip {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding-bottom: 120px; /* 给字幕留出底部区域 */
      }

      /* 字幕 */
      .clip.sub {
        z-index: 10;
        justify-content: flex-end;
        padding-bottom: 72px;
      }
      .sub span {
        font-size: 46px;
        line-height: 1.4;
        padding: 10px 28px;
        border-radius: 12px;
        background: rgba(5, 10, 20, 0.72);
        color: #ffffff;
      }

      /* s1 标题 */
      #s1-title {
        font-size: 120px;
        font-weight: 700;
        letter-spacing: 0.04em;
      }
      #s1-sub {
        margin-top: 28px;
        font-size: 44px;
        color: #8fb4e8;
      }

      /* s2 流水线 */
      #s2-head {
        font-size: 56px;
        font-weight: 700;
        margin-bottom: 90px;
      }
      .row {
        display: flex;
        align-items: center;
        gap: 36px;
      }
      .box {
        position: relative;
        width: 330px;
        height: 200px;
        border: 3px solid #3a5f99;
        border-radius: 20px;
        background: rgba(20, 36, 64, 0.85);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 14px;
      }
      .box .n {
        font-size: 30px;
        color: #8fb4e8;
      }
      .box .t {
        font-size: 42px;
        font-weight: 700;
      }
      /* 点亮层叠在框上，用 opacity 做动画（seek 安全） */
      .box .lit {
        position: absolute;
        inset: -3px;
        border: 3px solid #f2a541;
        border-radius: 20px;
        background: rgba(242, 165, 65, 0.12);
        box-shadow: 0 0 40px rgba(242, 165, 65, 0.45);
        opacity: 0;
      }
      .arrow {
        font-size: 56px;
        color: #6f95cf;
      }

      /* s3 时长条：宽度按每句真实时长比例 */
      #s3-head {
        font-size: 56px;
        font-weight: 700;
        margin-bottom: 70px;
      }
      #bars {
        display: flex;
        gap: 12px;
        width: 1400px;
      }
      .bar {
        height: 120px;
        border-radius: 14px;
        background: #1d3a66;
        border: 3px solid #3a5f99;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        transform-origin: left center;
      }
      .bar .id {
        font-size: 30px;
        color: #8fb4e8;
      }
      .bar .d {
        font-size: 38px;
        font-weight: 700;
      }
      .bar.now {
        background: #5a3d12;
        border-color: #f2a541;
      }

      /* s4 收尾 */
      #s4-text {
        font-size: 96px;
        font-weight: 700;
      }
      #s4-check {
        color: #5fd39a;
      }
      #s4-sub {
        margin-top: 24px;
        font-size: 40px;
        color: #8fb4e8;
      }
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{{TOTAL}}"
      data-width="1920"
      data-height="1080"
    >
      <section id="s1" class="clip" data-start="{{s1.start}}" data-duration="{{s1.dur}}" data-track-index="0">
        <h1 id="s1-title">代码即视频</h1>
        <p id="s1-sub">Claude 写 HTML，HyperFrames 渲染成 MP4</p>
      </section>

      <section id="s2" class="clip" data-start="{{s2.start}}" data-duration="{{s2.dur}}" data-track-index="0">
        <h2 id="s2-head">一条最小闭环</h2>
        <div class="row">
          <div class="box" id="b1"><div class="lit"></div><span class="n">01</span><span class="t">分镜脚本</span></div>
          <span class="arrow" id="a1">→</span>
          <div class="box" id="b2"><div class="lit"></div><span class="n">02</span><span class="t">HTML + GSAP</span></div>
          <span class="arrow" id="a2">→</span>
          <div class="box" id="b3"><div class="lit"></div><span class="n">03</span><span class="t">逐帧截图</span></div>
          <span class="arrow" id="a3">→</span>
          <div class="box" id="b4"><div class="lit"></div><span class="n">04</span><span class="t">合成 MP4</span></div>
        </div>
      </section>

      <section id="s3" class="clip" data-start="{{s3.start}}" data-duration="{{s3.dur}}" data-track-index="0">
        <h2 id="s3-head">时间轴由配音时长驱动</h2>
        <div id="bars"></div>
      </section>

      <section id="s4" class="clip" data-start="{{s4.start}}" data-duration="{{s4.dur}}" data-track-index="0">
        <p id="s4-text">跑通了 <span id="s4-check">✓</span></p>
        <p id="s4-sub">下一步：真实选题</p>
      </section>

      <!-- AUTO:MEDIA -->
    </div>
    <script>
      /* AUTO:TIMING */
      const IDS = ["L01", "L02", "L03", "L04"];

      // s3 时长条：按真实时长比例设宽度（加载时一次性计算，确定性）
      const bars = document.getElementById("bars");
      const sum = IDS.reduce((a, id) => a + T[id].dur, 0);
      IDS.forEach((id) => {
        const el = document.createElement("div");
        el.className = "bar" + (id === "L03" ? " now" : "");
        el.id = `bar-${id}`;
        el.style.width = `${((1400 - 12 * (IDS.length - 1)) * T[id].dur) / sum}px`;
        el.innerHTML = `<span class="id">${id}</span><span class="d">${T[id].dur.toFixed(1)} 秒</span>`;
        bars.appendChild(el);
      });

      const tl = gsap.timeline({ paused: true });

      // s1：跟着 L01
      tl.fromTo("#s1-title", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.7, ease: "power2.out" }, 0.1);
      tl.fromTo("#s1-sub", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" }, T.L01.start + 0.6);

      // s2：框依次出现，在解说说到每一步时点亮
      const s2 = T.L02.start - 0.15;
      tl.fromTo("#s2-head", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.5 }, s2);
      ["#b1", "#a1", "#b2", "#a2", "#b3", "#a3", "#b4"].forEach((sel, i) => {
        tl.fromTo(sel, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, s2 + 0.2 + i * 0.1);
      });
      ["#b1", "#b2", "#b3", "#b4"].forEach((sel, i) => {
        const t = T.L02.marks[i];
        tl.to(`${sel} .lit`, { opacity: 1, duration: 0.25 }, t);
        if (i < 3) tl.to(`${sel} .lit`, { opacity: 0.35, duration: 0.25 }, T.L02.marks[i + 1]);
      });

      // s3：时长条依次展开
      const s3 = T.L03.start - 0.15;
      tl.fromTo("#s3-head", { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.5 }, s3);
      IDS.forEach((id, i) => {
        tl.fromTo(`#bar-${id}`, { opacity: 0, scaleX: 0 }, { opacity: 1, scaleX: 1, duration: 0.45, ease: "power2.out" }, s3 + 0.3 + i * 0.25);
      });

      // s4：跟着 L04
      tl.fromTo("#s4-text", { opacity: 0, scale: 0.92 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.6)" }, T.L04.start - 0.1);
      tl.fromTo("#s4-sub", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.4 }, T.L04.start + 0.4);

      window.__timelines = window.__timelines || {};
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
