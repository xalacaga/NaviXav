"use strict";

/* Lecteur local : aucun document ni terme recherché ne quitte NaviXav. */
window.AircraftDocuments = (() => {
  const t = key => window.I18N.t(key);
  const tf = (key, values) => window.I18N.format(key, values);
  const node = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  };
  const button = (text, action) => {
    const element = node("button", "icon-btn", text);
    element.type = "button";
    element.addEventListener("click", action);
    return element;
  };

  let active = null;
  const inventories = new Map();

  function inventory(title, icao, refresh = false) {
    const params = new URLSearchParams({ title, icao });
    const key = params.toString();
    const cached = inventories.get(key);
    if (!refresh && cached && Date.now() - cached.time < 60000) return cached.request;
    const request = fetch(`/api/aircraft/documents?${params}`).then(response => {
      if (!response.ok) throw new Error("Documentation unavailable");
      return response.json();
    });
    inventories.set(key, { time: Date.now(), request });
    if (inventories.size > 8) inventories.delete(inventories.keys().next().value);
    request.catch(() => { if (inventories.get(key)?.request === request) inventories.delete(key); });
    return request;
  }

  function bindButton(button, context) {
    button.classList.add("hidden");
    inventory(context.title, context.icao).then(report => {
      if (!button.isConnected || !report.packages.some(item => item.documents.length)) return;
      button.classList.remove("hidden");
      button.addEventListener("click", () => open({ ...context, initialReport: report }));
    }).catch(() => {});
  }

  function keepOpen(panel, { title = "", icao = "" }) {
    if (!active || active.panel !== panel) return false;
    if (active.title === title && active.icao === icao) return true;
    active.close(false);
    return false;
  }

  function open({ panel, title = "", icao = "", onClose, initialReport = null } = {}) {
    if (!panel || active) return;
    const opener = document.activeElement;
    const original = document.createDocumentFragment();
    original.append(...panel.childNodes);
    const reader = node("section", "aircraft-documents-reader");
    reader.setAttribute("aria-labelledby", "aircraft-documents-title");
    const heading = node("h2", null, t("acf_docs_title"));
    heading.id = "aircraft-documents-title";
    const header = node("div", "aircraft-documents-header");
    const close = button(t("acf_docs_back"), () => closeReader());
    const refresh = button(t("acf_docs_refresh"), () => loadInventory());
    header.append(heading, refresh, close);
    const selectors = node("div", "aircraft-documents-selectors");
    const pdfSelect = node("select");
    const label = node("label", null, `${t("acf_docs_file")} · ${title || icao}`);
    label.append(pdfSelect);
    selectors.append(label);
    const form = node("form", "aircraft-documents-search");
    const query = node("input");
    query.type = "search";
    query.minLength = 2;
    query.maxLength = 120;
    query.required = true;
    query.placeholder = t("acf_docs_search_hint");
    query.setAttribute("aria-label", t("acf_docs_search_hint"));
    const search = node("button", "btn-primary", t("acf_docs_search"));
    search.type = "submit";
    const clear = button(t("acf_docs_clear"), () => {
      searchGeneration++;
      results.replaceChildren();
      body.classList.remove("has-results");
      query.value = "";
      search.disabled = !selected;
      query.focus();
    });
    form.append(query, search, clear);
    const status = node("p", "aircraft-documents-status");
    status.setAttribute("role", "status");
    const body = node("div", "aircraft-documents-body");
    const results = node("div", "aircraft-documents-results");
    results.setAttribute("aria-label", t("acf_docs_results"));
    const frame = node("iframe", "aircraft-documents-frame hidden");
    frame.title = t("acf_docs_title");
    body.append(results, frame);
    reader.append(header, selectors, form, status, body);
    panel.append(reader);
    panel.classList.add("reading-aircraft-documents");
    let documents = [];
    let selected = null;
    let documentGeneration = 0;
    let searchGeneration = 0;
    const controller = new AbortController();
    const isOpen = () => active?.reader === reader;
    const resize = () => {
      const top = Math.max(0, panel.getBoundingClientRect().top);
      reader.style.height = `${Math.max(300, window.innerHeight - top - 24)}px`;
    };
    const observer = new ResizeObserver(resize);
    observer.observe(document.querySelector(".topbar") || document.documentElement);
    window.addEventListener("resize", resize);
    function closeReader(restore = true) {
      active = null;
      controller.abort();
      observer.disconnect();
      window.removeEventListener("resize", resize);
      frame.removeAttribute("src");
      panel.classList.remove("reading-aircraft-documents");
      panel.replaceChildren(original);
      if (restore && onClose) onClose();
      if (restore && opener?.isConnected) opener.focus();
    }
    active = { panel, reader, title, icao, close: closeReader };
    const request = async (url, options = {}) => {
      const response = await fetch(url, { ...options, signal: controller.signal });
      if (!response.ok) throw new Error("Document unavailable");
      return response;
    };
    const jumpToPage = page => {
      const url = selected?.url;
      if (!url) return;
      frame.src = "about:blank";
      requestAnimationFrame(() => {
        if (isOpen() && selected?.url === url) frame.src = `${url}#page=${page}&view=FitH`;
      });
    };
    async function loadDocument() {
      const generation = ++documentGeneration;
      searchGeneration++;
      selected = null;
      frame.removeAttribute("src");
      frame.classList.add("hidden");
      results.replaceChildren();
      body.classList.remove("has-results");
      query.disabled = search.disabled = clear.disabled = true;
      const doc = pdfSelect.value === "" ? null : documents[Number(pdfSelect.value)];
      if (!doc) return;
      status.textContent = t("acf_docs_loading");
      try {
        await request(doc.url, { method: "HEAD" });
        if (!isOpen() || generation !== documentGeneration) return;
        selected = doc;
        frame.title = doc.name;
        frame.classList.remove("hidden");
        jumpToPage(1);
        status.textContent = doc.relative_path;
        query.disabled = search.disabled = clear.disabled = false;
      } catch (error) {
        if (isOpen() && generation === documentGeneration) status.textContent = t("acf_docs_failed");
      }
    }
    async function loadInventory() {
      refresh.disabled = pdfSelect.disabled = true;
      pdfSelect.replaceChildren();
      documents = [];
      loadDocument();
      status.textContent = t("acf_docs_loading");
      try {
        const report = initialReport || await inventory(title, icao, true);
        initialReport = null;
        if (!isOpen()) return;
        documents = report.packages.flatMap(item => item.documents.map(doc => ({
          ...doc, label: report.packages.length > 1 ? `${item.package} / ${doc.relative_path}` : doc.relative_path,
        })));
        if (!documents.length) { closeReader(); return; }
        for (const [index, doc] of documents.entries()) {
          pdfSelect.add(new Option(doc.label, String(index)));
        }
        pdfSelect.disabled = !documents.length;
        status.textContent = t("acf_docs_loading");
        loadDocument();
        if (!report.community_found) status.textContent = t("acf_docs_no_community");
      } catch (error) {
        if (isOpen()) status.textContent = t("acf_docs_failed");
      } finally {
        refresh.disabled = false;
      }
    }
    pdfSelect.addEventListener("change", loadDocument);
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (!selected || query.value.trim().length < 2) return;
      const generation = ++searchGeneration;
      const doc = selected;
      search.disabled = true;
      results.replaceChildren(node("p", null, t("acf_docs_searching")));
      body.classList.add("has-results");
      try {
        const data = await (await request(`${doc.url}/search?q=${encodeURIComponent(query.value.trim())}`)).json();
        if (!isOpen() || generation !== searchGeneration) return;
        results.replaceChildren(node("p", null, !data.text_available ? t("acf_docs_no_text")
          : data.total ? tf("acf_docs_found", { count: data.total }) : t("acf_docs_no_results")));
        if (data.limited) results.append(node("p", null, t("acf_docs_limited")));
        for (const match of data.matches) {
          const result = button("", () => jumpToPage(match.page));
          result.append(node("strong", null, tf("acf_docs_page", { page: match.page })),
            node("span", null, match.snippet));
          results.append(result);
        }
      } catch (error) {
        if (isOpen() && generation === searchGeneration) results.replaceChildren(node("p", null, t("acf_docs_search_failed")));
      } finally {
        if (generation === searchGeneration) search.disabled = !selected;
      }
    });
    reader.addEventListener("keydown", event => {
      if (event.key === "Escape") { event.preventDefault(); closeReader(); }
    });
    panel.scrollIntoView({ block: "start" });
    resize();
    close.focus();
    loadInventory();
  }
  return { open, keepOpen, bindButton };
})();
