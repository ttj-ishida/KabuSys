# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ / ツール群）のリポジトリです。  
この README はソースコード（src/kabusys 以下）を基にした概要、機能、セットアップ、使い方、およびディレクトリ構成をまとめたものです。

注意: 本リポジトリは複数のサブシステム（実行エンジン / 監視 / 研究 / AI 統合 / Paper Trading 検証など）を含みます。使い方に応じて環境変数を設定してください。

---

## プロジェクト概要

KabuSys は以下を想定したモジュール群です。

- 注文作成・送信・状態同期・再起動時リコンシリエーション（execution）
- 監視（システム稼働・注文滞留・ドローダウンなど）およびアラート（LINE）
- Paper Trading 用モックブローカーと検証レポート生成
- ファクター計算・特徴量探索などのリサーチツール（DuckDB 上の時系列データ参照）
- ニュースを LLM（OpenAI）でスコアリングして AI スコアを生成・利用（ai）
- ポートフォリオ構築、ポジションサイズ計算、リスク調整などのユーティリティ

設計上の特徴：
- 設定は環境変数（.env / .env.local を自動読み込み）で管理
- DuckDB を用いた時系列ファクター計算（prices_daily / raw_financials 等）
- SQLite により軽量な監視ログ / 注文ログを永続化
- Paper Trading は本番 DB と分離（専用 SQLite ファイル）
- OpenAI 呼び出しは適切なリトライ・バリデーションを実装

---

## 主な機能一覧

- execution
  - OrderManager / ExecutionEngine / RiskManager / Reconciler による発注ライフサイクル管理
  - BrokerClientFactory で実環境 or モックブローカーを切替
  - Paper Trading モード時は data/paper_trading.db に分離して記録
- monitoring
  - SystemMonitor: CPU / メモリ / ディスク / 実行プロセス存在確認 / データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）・約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション数上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じてフラグファイルを書き ExecutionEngine 停止を誘導
  - AlertManager: LINE Push によるアラート（クールダウン管理）
  - monitoring DB スキーマ（system_status / trade_logs / positions / risk_logs / dashboard）
  - streamlit ダッシュボード（read-only 接続）
- research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリ
- ai
  - news_nlp: raw_news を LLM でセンチメント化して ai_scores に書き込み（OpenAI）
  - regime_detector: ETF ma200 とマクロニュースを合成して市場レジーム判定（bull/neutral/bear）
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率 / 成立率 / レイテンシ等）
- portfolio
  - 銘柄候補選定・重み計算・ポジションサイズ決定・セクター制約の適用

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール  
   ※ pyproject.toml / requirements.txt が無い場合は主要なランタイム依存を手動インストールしてください。
   例:
   - pip install duckdb psutil requests streamlit openai

3. プロジェクトルートに .env を配置（任意）
   - リポジトリは .env / .env.local を自動読み込みします（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 主要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須：利用箇所に応じて）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須：実運用で使用）
   - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
   - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH — ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH — Kill Switch 用フラグ（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE — Paper Trading の約定動作: instant | partial | never | reject（デフォルト: instant）

---

## 使い方（主要コマンド / 実行例）

基本的にパッケージのトップレベルモジュールを直接実行します（PYTHONPATH に src を含めるかパッケージ化して実行）。

- 実行環境の例（ターミナル）:
  - export PYTHONPATH=src
  - export KABUSYS_ENV=paper_trading
  - export OPENAI_API_KEY=sk-xxxx

1) 監視ループを起動（SystemMonitor 単体）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
   - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず）。

2) 実行エンジンを起動（ExecutionEngine）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。運用モード（live）では実ブローカーを使用します（設定要）。
   - 起動時にプロセス優先度を「high」に設定する処理が実行されます（失敗しても続行）。

3) Streamlit ダッシュボード（監視 DB を参照）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を明示する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI スコアリング / レジーム判定（プログラム的呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=...)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - どちらも OPENAI_API_KEY が必要（引数で渡すことも可能）。

---

## 監視・安全機構のポイント

- KillSwitch
  - RiskMonitor がドローダウンやポジション上限のトリガーを検出した場合、指定パスに kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計です（Execution 側は起動時や定期的に kill.flag の存在をチェックする想定）。
  - kill.flag は既に存在する場合は上書きされません（冪等）。

- Monitoring DB（SQLite）スキーマ
  - system_status: CPU/メモリ/ディスク/プロセス OK の履歴
  - trade_logs: 発注イベントログ（latency_ms 列あり）
  - positions: 保有ポジション
  - risk_logs: 各種リスクアラート記録
  - dashboard: ダッシュボード集計（1行固定 id=1）

- Execution 側の再起動耐性
  - Reconciler により OrderSent 状態の注文をブローカーと突合・同期し、ポジション差分を検出してログ化します。

---

## 設定（.env の読み込み挙動）

- 自動読み込み順:
  - OS 環境変数（最優先）
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env`（既存未設定キーのみ設定）
  - 同じ場所の `.env.local`（`.env` の上書き。OS 環境変数は保護）

- 自動ロード無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env/.env.local の自動ロードを行いません（テスト等で使用）。

- .env のパースはシェル風（export を許容、クォートやインラインコメントに対応）です。必須変数が未設定の際には Settings のプロパティで ValueError が発生します。

---

## 既定値（主なパス / 値）

- DuckDB: data/kabusys.duckdb
- Monitoring SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag
- MONITOR_POLL_INTERVAL: 60 秒（環境変数で上書き可）
- PAPER_FILL_MODE: instant（instant | partial | never | reject）

---

## 主要モジュールの説明（ディレクトリ構成）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数 / 設定読み込み（Settings クラス）
- run_monitoring.py — SystemMonitor 単体のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト（paper_trading は専用 DB に分離）
- monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ永続化層（初期化スクリプト含む）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留 / 約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 操作ユーティリティ
  - alert_manager.py — LINE Push 通知（クールダウン管理）
  - monitoring_engine.py — 複数モニタを束ねるエンジン（テスト用 run_once / 本番用 run）
  - streamlit_dashboard.py — Streamlit ダッシュボード（監視 DB を read-only で表示）
- execution/
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, execution_engine.py など — 発注 / 状態管理 / リコンシリエーション
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュース記事の LLM による銘柄センチメントスコア化
  - regime_detector.py — ma200 とマクロニュースで市場レジーム判定（LLM 併用）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール

---

## 開発上の注意点 / ベストプラクティス

- 本番用の秘密情報（API キー・パスワード等）は OS 環境変数で渡すか、安全に管理してください。`.env` に直接書いた場合は漏洩リスクに注意。
- Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定して専用 DB を使用することで本番データと完全分離できます。
- OpenAI を利用する処理はネットワーク API 呼び出しのため、API キー・レート制限・課金に注意してください。news_nlp や regime_detector はリトライ・バックオフ・レスポンスバリデーションを備えていますが、過剰な呼び出しは避けてください。
- DuckDB / SQLite ファイルパスはデフォルトで data/ 以下ですが、配置やバックアップポリシーは運用に合わせて設計してください。
- Monitoring 系は監視データの永続化やリスク判定を行うため、十分なディスク容量・適切なパーミッションで運用してください。

---

README は実装ファイル群の主要点をまとめたものです。さらに詳しい API 仕様や実行エンジン内部の振る舞い（EngineConfig / RiskConfig 等）については、該当ソースコードの docstring を参照してください。必要があれば運用手順書や設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）を別途作成することを推奨します。