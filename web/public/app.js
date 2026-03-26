/**
 * 雲端翻譯前端：API 金鑰只存在瀏覽器 localStorage，請求直連 Google，不經站長伺服器。
 * 需配合 Google Cloud / AI Studio 將金鑰的 HTTP 參照位址設為本 Pages 網域。
 */
(function () {
  "use strict";

  const STORAGE_KEY = "translation_project_gemini_key_v1";
  const GLOSSARY_LIMIT = 10000;
  const MIN_SPLICE_LEN = 28;
  const MAX_SPLICE_LEN = 480;
  const BREAK_DELIMS = ["\n", "。", "！", "？", "．", ".", "!", "?"];

  const MODEL_OPTIONS = {
    "gemini-2.5-flash": "Gemini 2.5 Flash（建議）",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
  };

  const TARGET_LANGUAGE_OPTIONS = {
    "zh-TW": "繁體中文",
    ja: "日文",
    en: "英文",
    ko: "韓文",
  };

  const TARGET_PROMPTS = {
    "zh-TW": {
      glossaryHint: "請為每個術語提供建議的繁體中文譯名。",
      translateGoal: "流暢且優雅的繁體中文",
      summaryLead:
        "請為以下譯文生成一段 100 字以內的簡短摘要，使用繁體中文，重點說明主要內容與脈絡：\n\n",
    },
    ja: {
      glossaryHint:
        "各用語について、文脈に合った自然な日本語の訳語を付けてください。",
      translateGoal: "自然で読みやすい日本語",
      summaryLead:
        "以下の訳文を読み、日本語で内容と脈絡を押さえた短い要約をおおよそ 200 字以内で書いてください：\n\n",
    },
    en: {
      glossaryHint:
        "For each term, give a concise, natural English gloss or translation appropriate to the text.",
      translateGoal: "fluent, natural English",
      summaryLead:
        "Read the following translation and write a brief summary in English (about 80–120 words) capturing the main points and context:\n\n",
    },
    ko: {
      glossaryHint:
        "각 용어에 대해 문맥에 맞는 자연스러운 한국어 표기나 번역을 제시하세요.",
      translateGoal: "자연스럽고 읽기 쉬운 한국어",
      summaryLead:
        "다음 번역문을 바탕으로, 핵심 내용과 맥락을 담은 짧은 요약을 한국어로 약 200자 내외로 작성하세요：\n\n",
    },
  };

  function normalizeTargetLang(code) {
    return TARGET_PROMPTS[code] ? code : "zh-TW";
  }

  const GEMINI_BASE =
    "https://generativelanguage.googleapis.com/v1beta/models/";

  function stratifiedSnippet(text, limit) {
    const t = text.trim();
    if (t.length <= limit) return t;
    const third = Math.max(1, Math.floor(limit / 3));
    const head = t.slice(0, third);
    const midI = Math.max(0, Math.floor(t.length / 2) - Math.floor(third / 2));
    const mid = t.slice(midI, midI + third);
    const tail = t.slice(-third);
    return `${head}\n\n[… 文中省略 …]\n\n${mid}\n\n[… 文中省略 …]\n\n${tail}`;
  }

  function buildExtractGlossaryPrompt(text, targetLang) {
    const tl = normalizeTargetLang(targetLang);
    const cfg = TARGET_PROMPTS[tl];
    const snippet = stratifiedSnippet(text, GLOSSARY_LIMIT);
    return `
    你是一位專業的術語提取專家。請從以下文本中提取出 20-30 個關鍵術語（包含專有名詞、技術術語、高頻關鍵字）。
    ${cfg.glossaryHint}
    
    輸出格式請嚴格遵守 JSON 格式：
    {
        "glossary": [
            {"original": "term1", "translation": "譯名1"},
            {"original": "term2", "translation": "譯名2"}
        ]
    }
    
    文本內容：
    ${snippet}
    `;
  }

  function glossaryToPromptText(glossary) {
    if (typeof glossary === "string") return glossary;
    try {
      return JSON.stringify(glossary, null, 2);
    } catch {
      return String(glossary);
    }
  }

  function buildTranslatePrompt(chunk, glossary, prevSummary, targetLang) {
    const tl = normalizeTargetLang(targetLang);
    const cfg = TARGET_PROMPTS[tl];
    const gtxt = glossaryToPromptText(glossary);
    const ps = prevSummary || "";
    return `
    你是一位專業的翻譯專家，擅長將文本翻譯為${cfg.translateGoal}。
    
    請遵守以下規範：
    1. 參考術語表進行翻譯：${gtxt}
    2. 參考前文摘要以維持脈絡連貫性：${ps}
    3. 翻譯風格應自然流暢，避免翻譯腔。
    
    待翻譯文本：
    ${chunk}
    
    請直接輸出翻譯結果。
    `;
  }

  function buildSummaryPrompt(chunkTranslation, targetLang) {
    const tl = normalizeTargetLang(targetLang);
    const cfg = TARGET_PROMPTS[tl];
    return cfg.summaryLead + chunkTranslation;
  }

  function rfindAnyBreak(s) {
    let best = -1;
    for (const d of BREAK_DELIMS) {
      const j = s.lastIndexOf(d);
      if (j > best) best = j;
    }
    return best;
  }

  function splitTextWithOverlap(text, chunkSize, overlapSize) {
    if (!text) return [];
    const chunks = [];
    let start = 0;
    const textLength = text.length;

    while (start < textLength) {
      let end = start + chunkSize;
      if (end < textLength) {
        const searchStart = Math.max(start, end - 100);
        const searchEnd = Math.min(textLength, end + 100);
        const searchRange = text.slice(searchStart, searchEnd);
        const breakPoint = rfindAnyBreak(searchRange);
        if (breakPoint !== -1) end = searchStart + breakPoint + 1;
      } else {
        end = textLength;
      }
      const chunk = text.slice(start, end);
      if (chunk) chunks.push(chunk);
      if (end >= textLength) break;
      let nextStart = end - overlapSize;
      if (nextStart <= start) nextStart = start + Math.floor(chunkSize / 2);
      start = nextStart;
    }
    return chunks;
  }

  function joinTranslatedChunks(translations) {
    if (!translations.length) return "";
    const parts = [];
    const first = translations[0].trim();
    if (first) parts.push(first);
    for (let i = 1; i < translations.length; i++) {
      let nxt = translations[i].trim();
      if (!nxt) continue;
      if (!parts.length) {
        parts.push(nxt);
        continue;
      }
      const prev = parts[parts.length - 1];
      const upper = Math.min(prev.length, nxt.length, MAX_SPLICE_LEN);
      let trimmed = nxt;
      for (let len = upper; len >= MIN_SPLICE_LEN; len--) {
        if (prev.endsWith(nxt.slice(0, len))) {
          trimmed = nxt.slice(len).replace(/^\s+/, "");
          break;
        }
      }
      if (trimmed) parts.push(trimmed);
      else if (upper >= MIN_SPLICE_LEN) continue;
      else parts.push(nxt);
    }
    return parts.join("\n\n");
  }

  function parseGlossaryFromModel(raw) {
    if (raw == null || !String(raw).trim()) return raw;
    let s = String(raw).trim();
    if (s.startsWith("```")) {
      s = s.replace(/^```(?:json)?\s*/i, "").replace(/\s*```\s*$/, "");
    }
    s = s.trim();
    let start = s.indexOf("{");
    let end = s.lastIndexOf("}");
    if (start !== -1 && end > start) {
      try {
        return JSON.parse(s.slice(start, end + 1));
      } catch {
        /* fallthrough */
      }
    }
    start = s.indexOf("[");
    end = s.lastIndexOf("]");
    if (start !== -1 && end > start) {
      try {
        return JSON.parse(s.slice(start, end + 1));
      } catch {
        /* fallthrough */
      }
    }
    return s;
  }

  function extractTextFromGenerateJson(body) {
    const cands = body.candidates;
    if (!Array.isArray(cands) || !cands.length) return null;
    const content = cands[0].content;
    if (!content || !Array.isArray(content.parts)) return null;
    let out = "";
    for (const p of content.parts) {
      if (p.text) out += p.text;
    }
    const t = out.trim();
    return t || null;
  }

  async function generateText(apiKey, modelName, prompt) {
    const url =
      GEMINI_BASE +
      encodeURIComponent(modelName) +
      ":generateContent?key=" +
      encodeURIComponent(apiKey);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
      }),
    });
    const text = await res.text();
    let body;
    try {
      body = JSON.parse(text);
    } catch {
      throw new Error(
        "Gemini HTTP " + res.status + "：" + text.slice(0, 200)
      );
    }
    if (!res.ok) {
      const err =
        body.error && body.error.message
          ? body.error.message
          : JSON.stringify(body).slice(0, 400);
      throw new Error("Gemini API：" + err);
    }
    const extracted = extractTextFromGenerateJson(body);
    if (!extracted)
      throw new Error("模型未回傳文字（可能遭安全審查阻擋）。");
    return extracted;
  }

  async function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  async function generateWithRetry(apiKey, modelName, prompt, maxRetries) {
    let lastErr;
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await generateText(apiKey, modelName, prompt);
      } catch (e) {
        lastErr = e;
        const msg = String(e.message || e).toLowerCase();
        const retry =
          msg.includes("429") ||
          msg.includes("quota") ||
          msg.includes("resource") ||
          msg.includes("503") ||
          msg.includes("500") ||
          msg.includes("unavailable");
        if (!retry || attempt === maxRetries - 1) throw e;
        await sleep(1500 * Math.pow(2, attempt));
      }
    }
    throw lastErr;
  }

  async function readFileAsText(file) {
    const name = (file.name || "").toLowerCase();
    const buf = await file.arrayBuffer();

    if (name.endsWith(".txt")) {
      return new TextDecoder("utf-8", { fatal: false }).decode(buf);
    }

    if (name.endsWith(".docx") && typeof mammoth !== "undefined") {
      const r = await mammoth.extractRawText({ arrayBuffer: buf });
      return r.value || "";
    }

    if (name.endsWith(".pdf") && typeof pdfjsLib !== "undefined") {
      pdfjsLib.GlobalWorkerOptions.workerSrc =
        "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
      const pdf = await pdfjsLib.getDocument({ data: buf }).promise;
      let full = "";
      for (let p = 1; p <= pdf.numPages; p++) {
        const page = await pdf.getPage(p);
        const tc = await page.getTextContent();
        const line = tc.items.map((it) => it.str).join("");
        full += line + "\n";
      }
      return full;
    }

    throw new Error(
      "不支援此格式。請用 .txt / .docx / .pdf，或將文字貼在文字框。"
    );
  }

  function logLine(msg) {
    const el = document.getElementById("log");
    el.textContent += msg + "\n";
    el.scrollTop = el.scrollHeight;
  }

  function clearLog() {
    document.getElementById("log").textContent = "";
  }

  function loadKey() {
    try {
      return localStorage.getItem(STORAGE_KEY) || "";
    } catch {
      return "";
    }
  }

  function saveKey(key) {
    try {
      if (key) localStorage.setItem(STORAGE_KEY, key);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }

  function fillModelSelect() {
    const sel = document.getElementById("model");
    sel.innerHTML = "";
    for (const [id, label] of Object.entries(MODEL_OPTIONS)) {
      const o = document.createElement("option");
      o.value = id;
      o.textContent = label;
      sel.appendChild(o);
    }
  }

  function fillTargetLangSelect() {
    const sel = document.getElementById("targetLang");
    if (!sel) return;
    sel.innerHTML = "";
    for (const [id, label] of Object.entries(TARGET_LANGUAGE_OPTIONS)) {
      const o = document.createElement("option");
      o.value = id;
      o.textContent = label;
      sel.appendChild(o);
    }
  }

  async function runPipeline() {
    const errEl = document.getElementById("error");
    const outEl = document.getElementById("output");
    const btn = document.getElementById("runBtn");
    errEl.textContent = "";
    outEl.value = "";
    clearLog();

    const apiKey = document.getElementById("apiKey").value.trim();
    if (!apiKey) {
      errEl.textContent = "請輸入 Gemini API 金鑰。";
      return;
    }

    const modelId = document.getElementById("model").value;
    const targetLang = document.getElementById("targetLang").value;
    const chunkSize = parseInt(document.getElementById("chunkSize").value, 10);
    const overlapSize = parseInt(
      document.getElementById("overlapSize").value,
      10
    );
    const fileInput = document.getElementById("file");
    const pasteEl = document.getElementById("paste");

    let sourceText = (pasteEl.value || "").trim();
    if (fileInput.files && fileInput.files[0]) {
      logLine("讀取檔案…");
      sourceText = (await readFileAsText(fileInput.files[0])).trim();
    }

    if (!sourceText) {
      errEl.textContent = "請貼上原文或選擇檔案。";
      return;
    }

    if (document.getElementById("rememberKey").checked) saveKey(apiKey);
    else saveKey("");

    btn.disabled = true;
    try {
      logLine("正在提取術語表…");
      const glossaryRaw = await generateWithRetry(
        apiKey,
        modelId,
        buildExtractGlossaryPrompt(sourceText),
        5
      );
      const glossary = parseGlossaryFromModel(glossaryRaw);
      logLine("術語表完成。");

      logLine("正在切段…");
      const chunks = splitTextWithOverlap(sourceText, chunkSize, overlapSize);
      logLine("共 " + chunks.length + " 段。");

      const translations = [];
      let prevSummary = "";
      for (let i = 0; i < chunks.length; i++) {
        logLine("翻譯第 " + (i + 1) + "/" + chunks.length + " 段…");
        const translated = await generateWithRetry(
          apiKey,
          modelId,
          buildTranslatePrompt(
            chunks[i],
            glossary,
            prevSummary,
            targetLang
          ),
          5
        );
        translations.push(translated);
        prevSummary = await generateWithRetry(
          apiKey,
          modelId,
          buildSummaryPrompt(translated, targetLang),
          5
        );
      }

      const joined = joinTranslatedChunks(translations);
      outEl.value = joined;
      logLine("完成。");
    } catch (e) {
      const msg = e.message || String(e);
      errEl.textContent = msg;
      logLine("錯誤：" + msg);
      if (
        msg.toLowerCase().includes("cors") ||
        msg.toLowerCase().includes("network")
      ) {
        errEl.textContent +=
          " 若為 CORS，請在 Google Cloud 將金鑰的「網站限制」加入本頁來源網域（請見下方說明）。";
      }
    } finally {
      btn.disabled = false;
    }
  }

  function init() {
    fillModelSelect();
    fillTargetLangSelect();
    const saved = loadKey();
    if (saved) document.getElementById("apiKey").value = saved;

    document.getElementById("runBtn").addEventListener("click", () => {
      runPipeline();
    });
    document.getElementById("clearKeyBtn").addEventListener("click", () => {
      document.getElementById("apiKey").value = "";
      saveKey("");
    });
    document.getElementById("dlTxt").addEventListener("click", () => {
      const t = document.getElementById("output").value;
      if (!t) return;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(
        new Blob([t], { type: "text/plain;charset=utf-8" })
      );
      a.download = "譯文.txt";
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
