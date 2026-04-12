# KabuSys — README

このリポジトリは日本株向けの自動売買 / 監視 / 研究ユーティリティ群をまとめたパッケージです。  
本READMEはコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 株式トレーディングの Execution（発注・状態管理・リコンシリエーション）
- モニタリング（プロセスの生存確認、データ鮮度、滞留注文・約定異常検知、リスク監視）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限等）
- 研究用ファクター計算 / 特徴量解析（DuckDB を利用）
- AI を利用したニュースセンチメント評価・市場レジーム判定（OpenAI API）
- ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

主要設計方針の例：
- DuckDB / SQLite を利用したローカル分析と監視ログ永続化
- 本番/テスト（paper_trading）環境の分離（paper_trading は専用 SQLite を使用）
- LLM 呼び出しは冪等 / フェイルセーフにして部分失敗を許容
- datetime.today() 等の直接参照を避け、ルックアヘッドバイアス対策を実施

---

## 主な機能一覧

- Execution
  - 発注管理（OrderManager）
  - ブローカーとの同期再構築（Reconciler）
  - Risk 管理 / 注文リポジトリ（SQLite）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検知
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 銘柄候補選定、等金額/スコア配分、リスク調整、株数算出（単元丸め含む）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC 計算・統計サマリ
- AI
  - news_nlp.score_news: ニュースを LLM でセンチメント評価して ai_scores テーブルへ書込
  - regime_detector.score_regime: マクロニュース + ma200 乖離で市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## 必要条件 / 推奨環境

- Python 3.10+（typing のユニオン記法などを使用）
- 推奨パッケージ（主な依存）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- OS: Linux / macOS / Windows（process priority の一部はプラットフォーム依存）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
# または requirements.txt がある場合
# pip install -r requirements.txt
```

---

## 環境変数（主要）

自動でプロジェクトルートの `.env` / `.env.local` をロードします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数とデフォルト値 / 備考：

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: 監視 DB デフォルト "data/monitoring.db"
- PAPER_TRADING_SQLITE_PATH: paper_trading 時の DB デフォルト "data/paper_trading.db"
- PAPER_FILL_MODE: paper_trading のモック約定挙動 ("instant" | "partial" | "never" | "reject")（デフォルト "instant"）
- PID_FILE_PATH: デフォルト "data/execution.pid"
- KILL_FLAG_PATH: デフォルト "data/kill.flag"
- KILL_FLAG_CLEAR_ON_START: "1" で起動時に kill.flag をクリア
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

注意: Settings クラスは必要な環境変数が未設定の場合に ValueError を投げます（必須値は _require で保護）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env をプロジェクトルートに作成（.env.example を参考に必須項目を設定）
5. データディレクトリを作成（手動で作るか、起動時に自動生成される箇所あり）
   - 例: mkdir -p data

初回起動時に monitoring DB のテーブルは自動作成されます（init_monitoring_db を run スクリプトが呼びます）。

---

## 使い方（主要コマンド）

ソースツリーをモジュールとして実行できます（プロジェクトルートから実行を想定）。

- 監視ループ起動（SystemMonitor 単体スクリプト）
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を環境変数で変更:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- ExecutionEngine 起動（paper_trading では MockBroker を使用し別DBを利用）
```bash
# 本番（KABUSYS_ENV=live）や開発モードで実行
python -m kabusys.run_execution

# Paper Trading モード例
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
# Paper trading DB のパスを上書きしたい場合:
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Streamlit ダッシュボード
```bash
# デフォルト monitoring DB を参照（読み取り専用）
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポート（ツール）
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- プログラム的に AI 機能を呼び出す（例）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
```
- その他モジュールはパッケージ API（kabusys.portfolio.*, kabusys.research.* など）を直接インポートして利用可能です。

---

## 運用上の注意 / 仕様メモ

- Monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用します（監視データは分離されない点に注意）。
- Execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 sqlite を使用して本番 DB と完全分離します。
- プロセス優先度: run_monitoring/run_execution 起動時に set_process_priority("high") を試みます（psutil による設定。権限不足や未対応 OS の場合は警告のみ）。
- KillSwitch はデフォルトで data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計です。
- OpenAI API を使う機能は API キーが必須です。API 呼び出し部分はリトライやフォールバック（失敗時は neutral 値）を組み込んでいますが、充分なエラーハンドリングとコスト管理を行ってください。
- paper_verification_report の閾値（稼働率・成功率・送信率・P95 レイテンシ等）はツール内の定数で定義されています。必要に応じて変更してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイルと役割の一覧です（コードベースからの要約）。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロード、検証）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 分離）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite テーブル初期化 / MonitoringDB 書き込み読み出し
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止制御
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注フロー管理、送信/同期ロジック
    - reconciler.py — 再起動時の注文・ポジション照合
    - （その他 broker_factory, order_repository 等が存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・スケーリング・lot 丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI でセンチメント評価して ai_scores に書き込む
    - regime_detector.py — ETF ma200 + マクロセンチメントを合成して市場レジーム判定

---

## 開発・テストのヒント

- Settings は起動時に環境変数の検証を行うため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にすると制御しやすいです。
- AI 関連の外部呼び出しはモック化（unittest.mock.patch）しやすく設計されています（_call_openai_api を差し替え可能）。
- DuckDB / SQLite を使った関数群は外部 API に依存しない純粋関数として実装されている箇所が多いため、ユニットテストがしやすい構造になっています。

---

もし README に追記してほしい例（.env.example の例、詳細なコマンド、CI 設定、開発フロー等）があれば教えてください。