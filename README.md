# KabuSys

日本株自動売買システムの軽量コアライブラリ（リポジトリの抜粋）。  
この README はリポジトリ内の主要スクリプト・モジュールを元に作成した使い方ガイドです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤を想定したモジュール群です。主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）の起動・管理スクリプト
- システム監視（SystemMonitor / MonitoringEngine）とリスク監視（RiskMonitor）
- 発注・注文管理（OrderRepository / OrderManager 等 — 実装は別ファイル）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量解析）
- ニュース NLP（OpenAI を使ったセンチメントスコアリング）
- ペーパートレード用の検証レポート生成ツール
- 環境設定ウィザードと設定検証 CLI

設計方針の特徴：
- DuckDB（分析用）と SQLite（監視・注文ログ）を併用
- Paper Trading（模擬取引）は本番 DB と完全分離
- OpenAI を利用する NLP 系機能は API キー必須で、失敗時にも耐える設計
- 環境変数管理は `.env` をサポートし、自動読み込み機構あり

---

## 主な機能一覧

- 環境設定
  - 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- 実行
  - ExecutionEngine 起動: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading DB に記録
  - Monitoring 起動: python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
    - Monitoring は実行環境にかかわらず本番の sqlite_path を参照してログを残します
- 監視・アラート
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセスの監視、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格を検出してログ化
  - RiskMonitor: ドローダウンやポジション上限をチェックし、必要に応じて kill.flag を生成
  - KillSwitch: データ／フラグファイル経由で ExecutionEngine に停止シグナルを送出
- ポートフォリオ構築
  - 候補選定、等ウェイト・スコア加重、セクター上限適用、ポジションサイズ割当て（丸め込み）
- リサーチ
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア算出（kabusys.ai.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

以下はローカル開発向けの最低セットアップ手順の例です。

1. Python 環境
   - Python 3.10+ を推奨（型注釈で `|` の union を使用しているため）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージのインストール（最小）
   - pip install duckdb psutil openai
   - 解析用 YAML 検証を行う場合は: pip install pyyaml
   - （プロジェクトに requirements.txt がある場合はそれを使用してください）
4. .env の作成
   - 対話式で作成: python -m kabusys.config_setup
   - 最低限必要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development  # development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - OPENAI_API_KEY=sk-...
   - 注意: .env は絶対に Git にコミットしないでください
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

---

## 使い方

- 実行環境の切り替え
  - KABUSYS_ENV により動作モードを変更します:
    - development: 開発用（発注なし）
    - paper_trading: ペーパートレード（MockBroker を使用、データは paper_trading DB へ）
    - live: 本番（実発注）
- ExecutionEngine を起動する
  - python -m kabusys.run_execution
  - 挙動:
    - 起動直後に PID ファイル（data/execution.pid）を書き込む想定
    - data/stop_requested.flag が存在すると起動せず終了
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
    - Settings.kill_flag_clear_on_start が 1 のときは起動時に kill.flag を自動削除（本番では推奨しない）
- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視ループは data/stop_requested.flag を監視して終了
  - 監視ログは Settings.sqlite_path（デフォルト data/monitoring.db）に書き込まれる
- Kill Switch / 停止制御
  - KillSwitch は data/kill.flag（既定）に理由を書き込むことで ExecutionEngine に停止シグナルを送ります
  - 実行中のプロセスを安全に停止したい場合は kill.flag を作成または stop_requested.flag を作成してください
    - run_* スクリプトは stop_requested.flag を検知して終了します
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- AI 機能
  - OpenAI API を利用します（OPENAI_API_KEY 必須）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — execution 環境（development | paper_trading | live）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイルとディレクトリ（src/kabusys を基準にした抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねる実行ロジック
    - alert_manager.py       — （アラート送信管理；実装ファイルあり）
  - execution/                — 発注／実行関連（Engine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・丸め・キャップ処理
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（OpenAI 呼び出し）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

- data/                      — 実行時に使うファイル例
  - kill.flag                 — KillSwitch が書き込む停止フラグ
  - stop_requested.flag       — run_* スクリプトが監視する停止フラグ
  - execution.pid             — 実行エンジンの PID ファイル
  - monitoring.db, paper_trading.db, kabusys.duckdb など

---

## 実運用上の注意点

- 本番（KABUSYS_ENV=live）では .env に機密情報を正しく設定し、LINE 通知や KILL フラグの挙動を必ず確認してください（validate_config の `live` ガードがいくつかの注意を出します）。
- kill.flag / stop_requested.flag の扱いに注意してください。特に KILL_FLAG_CLEAR_ON_START=1 は本番では危険です（起動時に Kill Switch を自動クリアしてしまうため）。
- Monitoring は監視用 SQLite（Settings.sqlite_path）へ書き込みます。run_monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意してください。
- OpenAI API を利用する機能は API コスト・レート制限に注意して運用してください（ライブラリ側でリトライを実装していますが、運用ポリシーは別途設けてください）。

---

## 開発・拡張のヒント

- DuckDB 接続を引数に渡す設計なので、分析・リサーチ機能はローカルの小さな DB で単体検証できます。
- AI 呼び出しは個別のラッパー関数（_call_openai_api）を経由しているため、テスト時はモックで差し替えやすく設計されています。
- 設定検証（validate_config）や設定ウィザード（config_setup）は初期セットアップの自動化に便利です。

---

この README はコードベースの抜粋を元に作成しています。実際の運用・導入時にはプロジェクト内の追加ドキュメント（例: PortfolioConstruction.md, StrategyModel.md 等）や、実際の requirements.txt / deployment ドキュメントを参照してください。必要であれば README をさらに具体的な起動手順や環境変数の詳細（.env.example）を含めて拡張できます。