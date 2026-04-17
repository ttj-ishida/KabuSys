# KabuSys

KabuSys は日本株自動売買システムの一部実装（ポートフォリオ構築、監視、Execution 起動ラッパー、研究ユーティリティ、AI ニューススコアリング等）です。本リポジトリには、運用時に必要なモジュール群と起動スクリプトが含まれます。

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- 要求環境 / 依存パッケージ
- セットアップ手順
- 起動・使い方（代表例）
- 主要環境変数 / .env
- ディレクトリ構成（主要ファイル説明）
- 運用メモ / 注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買に関するライブラリ群（ポートフォリオ構築、リスク調整、ポジションサイズ計算、Execution 起動ラッパー、監視機能、AI によるニュースセンチメント評価、研究用ファクター計算など）を提供します。
- 内部的には SQLite（監視・注文ログ等）と DuckDB（時系列・ファクタ計算等）を用いてデータ永続化・集計を行います。
- OpenAI API を利用したニュース NLP / レジーム検出機能および LINE による通知機能を備えています（オプション）。

機能一覧
- 環境設定読み込み（.env / .env.local 自動読み込み、Settings クラス）
- ExecutionEngine 起動用スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時はモックブローカー／専用 SQLite を使用して本番 DB と分離
- 監視エンジン（run_monitoring.py / MonitoringEngine）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働確認 / データ鮮度チェック
  - TradeMonitor: 滞留注文監視、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 危険時に data/kill.flag を書き込み Execution を停止させる仕組み
  - AlertManager: LINE Messaging API によるプッシュ（クールダウン制御）
  - Streamlit ダッシュボード（読み取り専用）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重・スコア重み、セクター制限、レジーム乗数、発注株数決定（単元丸め・上限・スケーリング）
- 研究モジュール（research/*）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- AI モジュール（ai/*）
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルに書き込む
  - regime_detector: ETF（1321）の MA200 乖離 + マクロニュースでレジーム判定を行い market_regime テーブルへ書き込み
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

要求環境 / 依存パッケージ
- Python 3.10 以上（型ヒントに PEP 604 の '|' を利用）
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボードを使う場合)
- 標準モジュール: sqlite3, logging, threading, datetime, pathlib など

セットアップ手順（ローカル開発向け簡易）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （実運用では requirements.txt を用意して pip install -r requirements.txt を推奨）

3. プロジェクトルートに .env を配置（必要に応じて .env.local）
   - config.Settings は自動的にプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数が優先）
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. データディレクトリ
   - デフォルトの DB / フラグパスは data/ 以下を参照します（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag）
   - 必要に応じてディレクトリを作成: mkdir -p data

主要な環境変数（代表）
- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: Execution PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で上書き可能、デフォルト 60）

使い方（代表的な起動例）
- 監視プロセスを起動する
  - 実行: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止: 管理者が data/stop_requested.flag を作成するとループは検出して終了します（または Ctrl+C）

- ExecutionEngine を起動する
  - 実行: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとモックブローカーと data/paper_trading.db を使用して本番 DB と完全分離されます
  - 実行前に data/kill.flag が存在する場合、起動せずに終了します（停止フラグ運用）

- Streamlit ダッシュボード（監視用）
  - 実行: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（起動時に DB が無ければエラーを表示）

- Paper Trading 検証レポート生成
  - 実行: python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で指定可能

- AI モジュールの呼び出し（プログラム内）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="…")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="…")
  - いずれも api_key が None の場合は環境変数 OPENAI_API_KEY を参照します

運用メモ / 管理
- 停止フラグ
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を参照して自発終了や停止判定を行います（stop flag を置くと安全に停止できる運用が想定されています）。
- Kill Switch
  - RiskMonitor 等が閾値を超えた場合、KillSwitch が data/kill.flag に理由を書き込み Execution 停止を促します。手動で解除するには data/kill.flag を削除してください（rm data/kill.flag）。
- PID ファイル
  - run_execution は起動時に data/execution.pid を生成します。SystemMonitor は PID ファイルの有無とプロセス生存確認を行い、stale PID を検出すると削除してアラートログを残します。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等的にテーブル作成を行い、軽微なカラム追加（マイグレーション）も内部で扱います。

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py          — パッケージのメタ情報（__version__ 等）
  - config.py            — Settings クラス: 環境変数 / .env の取り扱いロジック
  - run_monitoring.py    — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py     — ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ（psutil 利用）
  - monitoring/
    - monitoring_db.py    — SQLite を使った監視ログ永続化層（テーブル定義・CRUD）
    - monitoring_engine.py— 各 Monitor を束ねたポーリングエンジン
    - system_monitor.py   — CPU/MEM/DISK/データ鮮度/プロセス監視
    - trade_monitor.py    — 滞留注文 / 約定異常検出
    - risk_monitor.py     — ドローダウン / ポジション上限監視
    - kill_switch.py      — kill.flag 管理
    - alert_manager.py    — LINE 通知ラッパー
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード（read-only）
  - execution/
    - order_manager.py, reconciler.py, ... — Execution 側の注文管理・再同期ロジック（Engine 本体は別モジュール）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py   — セクター制限・レジーム乗数
    - position_sizing.py   — 株数決定・単元丸め・投下資金スケーリング
  - research/
    - factor_research.py   — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py          — ニュース集約 → OpenAI でセンチメント解析 → ai_scores へ書き込み
    - regime_detector.py   — MA200 + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

例: 簡単な .env のテンプレート（運用前に必ず見直す）
- .env.example（例）
  - KABUSYS_ENV=development
  - JQUANTS_REFRESH_TOKEN=your_jquants_token
  - KABU_API_PASSWORD=your_kabu_password
  - OPENAI_API_KEY=sk-...
  - LINE_CHANNEL_ACCESS_TOKEN=
  - LINE_USER_ID=
  - PAPER_FILL_MODE=instant
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - SQLITE_PATH=data/monitoring.db
  - DUCKDB_PATH=data/kabusys.duckdb
  - LOG_LEVEL=INFO

トラブルシューティング / 注意点
- OpenAI の呼び出しはネットワーク・レート制限・レスポンスフォーマットに対するフォールトトレランスを設けていますが、API キーや料金設定が適切であることを確認してください。
- paper_trading モードは本番 DB と完全に分離するよう設計されています。運用時に誤って本番 DB を更新しないよう .env を必ず確認してください。
- duckdb / sqlite ファイルはディスク上に置かれるため、バックアップや容量監視を行ってください。SystemMonitor はデフォルトでルート（/）のディスク使用率を監視します（必要に応じ disk_path を設定）。
- Python バージョンは 3.10 以上を推奨します（型ヒントに PEP 604 を使用）。

---

この README はコードベースの主要な使い方と構成をまとめたものです。実運用・デプロイ時はログ設定、永続化先、バックアップ、監視の通知先、API キーの管理などを適切に設計して運用してください。必要であれば README を補足して CI/CD、systemd ユニット、Dockerfile、requirements.txt などの具体的なデプロイ手順を追加できます。