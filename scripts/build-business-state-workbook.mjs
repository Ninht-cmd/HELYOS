import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { SpreadsheetFile, Workbook } from "file:///C:/Users/emezr/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const HELYOS_ROOT = process.env.HELYOS_ROOT || "C:\\Users\\emezr\\Desktop\\HELYOS";
const JARVIS_ROOT = process.env.JARVIS_ROOT || path.join(HELYOS_ROOT, "apps", "jarvis-kernel");
const NVIDIA_ROOT = process.env.NVIDIA_LAB_ROOT || "C:\\Users\\emezr\\WORKSPACE\\NVIDIA-LAB";
const OSS_ROOT = process.env.OPEN_SOURCE_LAB_ROOT || "C:\\Users\\emezr\\WORKSPACE\\OPEN-SOURCE-LAB";
const OUT_DIR = process.env.BUSINESS_STATE_OUT || path.join(HELYOS_ROOT, "data", "business-state");
const OUT_XLSX = path.join(OUT_DIR, "helyos-business-state.xlsx");

const COLORS = {
  ink: "#111827",
  muted: "#6B7280",
  line: "#D1D5DB",
  navy: "#0B1F3A",
  teal: "#0F766E",
  green: "#16A34A",
  blue: "#2563EB",
  amber: "#D97706",
  red: "#DC2626",
  bg: "#F8FAFC",
  white: "#FFFFFF",
};

function money(value) {
  return Number(value || 0);
}

async function readJson(file, fallback) {
  try {
    const raw = await fs.readFile(file, "utf8");
    return JSON.parse(raw.replace(/^\uFEFF/, ""));
  } catch {
    return fallback;
  }
}

function parseTsv(text) {
  text = text.replace(/^\uFEFF/, "");
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) return [];
  const clean = (s) => s.replace(/^"|"$/g, "").replace(/""/g, '"');
  const headers = lines[0].split("\t").map(clean);
  return lines.slice(1).map((line) => {
    const cells = line.split("\t").map(clean);
    return Object.fromEntries(headers.map((h, i) => [h, cells[i] ?? ""]));
  });
}

async function readTsv(file) {
  try {
    return parseTsv(await fs.readFile(file, "utf8"));
  } catch {
    return [];
  }
}

async function countLocalRepos(root) {
  const githubDir = path.join(root, "github");
  const bareDir = path.join(root, "github-bare-fallback");
  let workingTree = 0;
  try {
    const owners = await fs.readdir(githubDir, { withFileTypes: true });
    for (const owner of owners.filter((entry) => entry.isDirectory())) {
      const repos = await fs.readdir(path.join(githubDir, owner.name), { withFileTypes: true });
      workingTree += repos.filter((entry) => entry.isDirectory()).length;
    }
  } catch {
    workingTree = 0;
  }

  let bareFallback = 0;
  try {
    const repos = await fs.readdir(bareDir, { withFileTypes: true });
    bareFallback = repos.filter((entry) => entry.isDirectory() && entry.name.endsWith(".git")).length;
  } catch {
    bareFallback = 0;
  }

  return { workingTree, bareFallback, total: workingTree + bareFallback };
}

function helyosState() {
  const code = `
import json
from jarvis_kernel.context import build_default_context
from jarvis_kernel.business.portfolio import seed_known_businesses

ctx = build_default_context()
if not ctx.portfolio.list():
    seed_known_businesses(ctx.portfolio)

entries = []
if ctx.ledger is not None:
    for b in ctx.portfolio.list():
        for e in ctx.ledger.entries(b.name, 200):
            entries.append(e.to_dict())

print(json.dumps({
    "ledger": ctx.ledger.global_summary() if ctx.ledger is not None else {},
    "portfolio": ctx.portfolio.summary(),
    "entries": entries,
}, ensure_ascii=False))
`;
  const env = {
    ...process.env,
    PYTHONPATH: "src",
    PYTHONIOENCODING: "utf-8",
  };
  const result = spawnSync("python", ["-c", code], {
    cwd: JARVIS_ROOT,
    env,
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  const lines = (result.stdout || "").trim().split(/\r?\n/).filter(Boolean);
  const jsonLine = [...lines].reverse().find((line) => line.trim().startsWith("{"));
  if (!jsonLine) {
    return { ledger: { recettes_eur: 0, depenses_eur: 0, solde_eur: 0, par_business: [] }, portfolio: [], entries: [] };
  }
  return JSON.parse(jsonLine);
}

function statusCount(items) {
  return Object.fromEntries((items || []).map((x) => [x.status, Number(x.count || 0)]));
}

function hfCounts(items) {
  const out = {};
  for (const item of items || []) {
    const kind = item.kind || "unknown";
    out[kind] ||= {};
    out[kind][item.status || "unknown"] = Number(item.count || 0);
  }
  return out;
}

function setTitle(sheet, title, subtitle = "") {
  sheet.getRange("A1:H1").merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 18 },
  };
  sheet.getRange("A2:H2").merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A2").format = {
    fill: "#E5E7EB",
    font: { color: COLORS.ink, size: 10 },
  };
}

function writeRows(sheet, startRow, startCol, rows) {
  if (!rows.length) return;
  const width = Math.max(...rows.map((r) => r.length));
  const matrix = rows.map((r) => [...r, ...Array(width - r.length).fill(null)]);
  sheet.getRangeByIndexes(startRow, startCol, matrix.length, width).values = matrix;
}

function formatTable(sheet, range, headerColor = COLORS.teal) {
  const r = sheet.getRange(range);
  r.format.borders = { preset: "all", style: "thin", color: COLORS.line };
  const firstRow = range.split(":")[0].replace(/[0-9]/g, "");
  const lastCol = range.split(":")[1].replace(/[0-9]/g, "");
  const row = range.match(/\d+/)?.[0] || "1";
  sheet.getRange(`${firstRow}${row}:${lastCol}${row}`).format = {
    fill: headerColor,
    font: { bold: true, color: COLORS.white },
  };
}

function autofit(sheet, range = "A:H") {
  try {
    sheet.getRange(range).format.autofitColumns();
    sheet.getRange(range).format.autofitRows();
  } catch {
    // Autofit is best-effort; export should not depend on it.
  }
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });

  const generatedAt = new Date().toISOString();
  const helyos = helyosState();
  const nvidiaGithub = await readJson(path.join(NVIDIA_ROOT, "catalogs", "repos-all-summary-final.json"), {});
  const nvidiaHf = await readJson(path.join(NVIDIA_ROOT, "catalogs", "huggingface-summary-final.json"), {});
  const nvidiaLfs = await readJson(path.join(NVIDIA_ROOT, "catalogs", "huggingface-lfs-phase3.json"), []);
  const ossCatalog = await readJson(path.join(OSS_ROOT, "catalogs", "github-open-source-summary-latest.json"), {});
  const ossClone = await readJson(path.join(OSS_ROOT, "catalogs", "github-open-source-clone-summary-latest.json"), {});
  const ossRows = await readTsv(ossClone.report || "");
  const ossInventory = await countLocalRepos(OSS_ROOT);

  const nvStatus = statusCount(nvidiaGithub.by_status);
  const nvGithubLocal = (nvStatus.cloned || 0) + (nvStatus.exists || 0) + (nvStatus.fallback_bare || 0);
  const hf = hfCounts(nvidiaHf.by_kind_status);
  const hfLocal = Object.values(hf).reduce((sum, row) => sum + (row.cloned || 0) + (row.exists || 0), 0);
  const hfGated = Object.values(hf).reduce((sum, row) => sum + (row.gated_auth_required || 0), 0);
  const ossStatus = statusCount(ossClone.by_status);
  const ossLocal = (ossStatus.cloned || 0) + (ossStatus.exists || 0) + (ossStatus.fallback_bare || 0);

  const workbook = Workbook.create();
  const dashboard = workbook.worksheets.add("Dashboard");
  const rentrees = workbook.worksheets.add("Rentrees");
  const portfolio = workbook.worksheets.add("Portfolio");
  const nvidia = workbook.worksheets.add("NVIDIA");
  const openSource = workbook.worksheets.add("OpenSource");
  const sources = workbook.worksheets.add("Sources");

  for (const ws of [dashboard, rentrees, portfolio, nvidia, openSource, sources]) {
    ws.showGridLines = false;
  }

  setTitle(dashboard, "HELYOS Business State", `Refresh local: ${generatedAt}`);
  writeRows(dashboard, 3, 0, [
    ["KPI", "Valeur", "", "Infrastructure", "Valeur", "", "Open source", "Valeur"],
    ["Rentrees EUR", null, "", "NVIDIA GitHub local", nvGithubLocal, "", "GitHub general local total", ossInventory.total || ossLocal],
    ["Depenses EUR", null, "", "NVIDIA Hugging Face local", hfLocal, "", "GitHub general catalogue", Number(ossCatalog.count || 0)],
    ["Solde EUR", null, "", "HF gated/licence", hfGated, "", "Dernier lot local", ossLocal],
    ["Business suivis", helyos.portfolio.length + 1, "", "Artifacts LFS lourds", nvidiaLfs.length, "", "Libre disque C: GB", Number(ossClone.free_gb || 0)],
  ]);
  dashboard.getRange("B5").formulas = [["=Rentrees!I2"]];
  dashboard.getRange("B6").formulas = [["=Rentrees!I3"]];
  dashboard.getRange("B7").formulas = [["=Rentrees!I4"]];
  dashboard.getRange("A4:H8").format.borders = { preset: "all", style: "thin", color: COLORS.line };
  dashboard.getRange("A4:B4").format = { fill: COLORS.teal, font: { bold: true, color: COLORS.white } };
  dashboard.getRange("D4:E4").format = { fill: COLORS.blue, font: { bold: true, color: COLORS.white } };
  dashboard.getRange("G4:H4").format = { fill: COLORS.amber, font: { bold: true, color: COLORS.white } };
  dashboard.getRange("B5:B7").format.numberFormat = "#,##0.00 EUR";
  dashboard.getRange("E5:E8").format.numberFormat = "#,##0";
  dashboard.getRange("H5:H7").format.numberFormat = "#,##0";
  dashboard.getRange("A10:H10").merge();
  dashboard.getRange("A10").values = [["Decision: aucune action externe, aucune depense, aucun trade. Ce classeur est un cockpit de lecture et de pilotage."]];
  dashboard.getRange("A10").format = { fill: "#FEF3C7", font: { bold: true, color: "#92400E" } };
  autofit(dashboard, "A:H");

  setTitle(rentrees, "Rentrees et caisse", "Source: HELYOS Ledger local. Les cellules A:F peuvent etre completees/importees dans Google Sheets.");
  const entryRows = (helyos.entries || []).map((e) => [
    e.ts ? new Date(e.ts * 1000) : null,
    e.business || "",
    e.kind || "",
    money(e.amount_eur),
    e.label || "",
    e.id || "",
  ]);
  const rentreeRows = [
    ["Date", "Business", "Type", "Montant EUR", "Libelle", "ID"],
    ...(entryRows.length ? entryRows : [[null, "", "", null, "Aucune ecriture HELYOS pour l'instant", ""]]),
  ];
  writeRows(rentrees, 4, 0, rentreeRows);
  formatTable(rentrees, `A5:F${5 + rentreeRows.length - 1}`);
  rentrees.getRange("D6:D205").format.numberFormat = "#,##0.00 EUR";
  rentrees.getRange("H1:I4").values = [
    ["KPI", "Valeur"],
    ["Recettes", null],
    ["Depenses", null],
    ["Solde", null],
  ];
  rentrees.getRange("I2").formulas = [["=SUMIF(C6:C205,\"recette\",D6:D205)"]];
  rentrees.getRange("I3").formulas = [["=SUMIF(C6:C205,\"depense\",D6:D205)"]];
  rentrees.getRange("I4").formulas = [["=I2-I3"]];
  rentrees.getRange("I2:I4").format.numberFormat = "#,##0.00 EUR";
  formatTable(rentrees, "H1:I4", COLORS.navy);
  autofit(rentrees, "A:I");

  setTitle(portfolio, "Portfolio HELYOS", "Business, statuts, metriques et taches ouvertes.");
  const portfolioRows = [
    ["Business", "Type", "Status", "Revenue EUR", "Solde EUR", "Open tasks", "Metrics JSON"],
    ...helyos.portfolio.map((b) => [
      b.name,
      b.kind,
      b.status,
      money(b.metrics?.revenue_eur ?? b.metrics?.revenu_direct_eur),
      money(b.metrics?.solde_eur),
      Number(b.open_tasks || 0),
      JSON.stringify(b.metrics || {}),
    ]),
    [
      "NVIDIA Lab",
      "infrastructure",
      `GitHub ${nvGithubLocal}/${Number(nvidiaGithub.attempted || 0)}; HF ${hfLocal}/${Number(nvidiaHf.entries || 0)}`,
      0,
      0,
      hfGated,
      JSON.stringify({ nvidia_github_local: nvGithubLocal, huggingface_local: hfLocal, gated: hfGated }),
    ],
  ];
  writeRows(portfolio, 4, 0, portfolioRows);
  formatTable(portfolio, `A5:G${5 + portfolioRows.length - 1}`, COLORS.teal);
  portfolio.getRange("D6:E105").format.numberFormat = "#,##0.00 EUR";
  autofit(portfolio, "A:G");

  setTitle(nvidia, "NVIDIA Lab", "Miroir local NVIDIA GitHub + Hugging Face + gros artifacts LFS.");
  const nvidiaRows = [
    ["Bloc", "Metric", "Valeur", "Chemin/Rapport"],
    ["GitHub", "Traites", Number(nvidiaGithub.attempted || 0), nvidiaGithub.report || ""],
    ["GitHub", "Disponibles localement", nvGithubLocal, nvidiaGithub.repos_all || ""],
    ["GitHub", "Fallback bare", Number(nvStatus.fallback_bare || 0), nvidiaGithub.bare_fallback || ""],
    ["HuggingFace", "Entrees", Number(nvidiaHf.entries || 0), nvidiaHf.report || ""],
    ["HuggingFace", "Disponibles localement", hfLocal, nvidiaHf.destination || ""],
    ["HuggingFace", "Gated/licence", hfGated, "Validation manuelle requise"],
    ...nvidiaLfs.map((x) => ["Artifact LFS", x.name || "", Number(x.size_gb || 0), x.path || ""]),
  ];
  writeRows(nvidia, 4, 0, nvidiaRows);
  formatTable(nvidia, `A5:D${5 + nvidiaRows.length - 1}`, COLORS.blue);
  nvidia.getRange("C6:C105").format.numberFormat = "#,##0.00";
  autofit(nvidia, "A:D");

  setTitle(openSource, "Open source GitHub general", "Catalogue strategique par topics; clones legers et idempotents.");
  const openRows = [
    ["Repo", "Status", "Stars", "Language", "URL", "Path"],
    ...ossRows.slice(0, 120).map((r) => [
      r.full_name || "",
      r.status || "",
      Number(r.stars || 0),
      r.language || "",
      r.url || "",
      r.path || "",
    ]),
  ];
  writeRows(openSource, 4, 0, openRows);
  formatTable(openSource, `A5:F${5 + openRows.length - 1}`, COLORS.amber);
  openSource.getRange("C6:C205").format.numberFormat = "#,##0";
  autofit(openSource, "A:F");

  setTitle(sources, "Sources et refresh", "Chemins locaux utilises par ce classeur.");
  const sourceRows = [
    ["Nom", "Chemin", "Etat"],
    ["HELYOS", HELYOS_ROOT, "code local"],
    ["Jarvis Kernel", JARVIS_ROOT, "source Python"],
    ["NVIDIA-LAB", NVIDIA_ROOT, "rapports + depots"],
    ["OPEN-SOURCE-LAB", OSS_ROOT, "catalogues + clones"],
    ["Workbook", OUT_XLSX, "genere"],
    ["NVIDIA GitHub summary", path.join(NVIDIA_ROOT, "catalogs", "repos-all-summary-final.json"), "lu"],
    ["NVIDIA HF summary", path.join(NVIDIA_ROOT, "catalogs", "huggingface-summary-final.json"), "lu"],
    ["OSS clone summary", path.join(OSS_ROOT, "catalogs", "github-open-source-clone-summary-latest.json"), "lu"],
  ];
  writeRows(sources, 4, 0, sourceRows);
  formatTable(sources, `A5:C${5 + sourceRows.length - 1}`, COLORS.navy);
  autofit(sources, "A:C");

  const inspect = await workbook.inspect({
    kind: "workbook,sheet,table,formula",
    maxChars: 6000,
    tableMaxRows: 4,
    tableMaxCols: 6,
  });
  await fs.writeFile(path.join(OUT_DIR, "helyos-business-state.inspect.ndjson"), inspect.ndjson || String(inspect), "utf8");

  const preview = await workbook.render({ sheetName: "Dashboard", autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(OUT_DIR, "helyos-business-state-dashboard.png"), new Uint8Array(await preview.arrayBuffer()));

  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(OUT_XLSX);

  await fs.writeFile(path.join(OUT_DIR, "helyos-business-state.summary.json"), JSON.stringify({
    generated_at: generatedAt,
    workbook: OUT_XLSX,
    preview: path.join(OUT_DIR, "helyos-business-state-dashboard.png"),
    helyos_ledger: helyos.ledger,
    nvidia: { github_local: nvGithubLocal, github_attempted: Number(nvidiaGithub.attempted || 0), hf_local: hfLocal, hf_entries: Number(nvidiaHf.entries || 0), hf_gated: hfGated },
    open_source: {
      catalogued: Number(ossCatalog.count || 0),
      local: ossInventory.total || ossLocal,
      latest_batch_local: ossLocal,
      attempted: Number(ossClone.attempted || 0),
      working_tree: ossInventory.workingTree,
      bare_fallback: ossInventory.bareFallback,
      free_gb: Number(ossClone.free_gb || 0),
    },
  }, null, 2), "utf8");

  console.log(`Workbook: ${OUT_XLSX}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
