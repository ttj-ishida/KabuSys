# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした Python コードベースです。本 README はリポジトリ内の主要コンポーネント、セットアップ手順、基本的な使い方、およびディレクトリ構成をまとめたものです。

注意: ソースは `src/` 配下に配置されています。実行時には `PYTHONPATH=src` を通すか、パッケージをインストールして利用してください（例: `pip install -e .`）。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: 注文作成・送信、リスク管理、リコンシリエーション等を行う実行パス
- 監視（Monitoring）: システム状態、注文滞留、リスクイベントの監視とログ化、LINE 通知、kill flag による停止制御
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ決定、セクター制限などの純粋関数群
- 研究（Research）: ファクター計算、特徴量探索、IC 計算などの分析ユーティリティ（DuckDB 使用）
- AI 関連: ニュースの NLP スコアリング、マクロセンチメントに基づく市場レジーム判定（OpenAI 利用）
- ツール: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード等
- 設定管理: `.env` / 環境変数ベースの設定読み込みと検証

---

## 主な機能一覧

- SystemMonitor: CPU/メモリ/ディスクの監視、データ鮮度確認、実行プロセスの生存確認
- TradeMonitor: 注文滞留（stale order）や約定の価格異常検出
- RiskMonitor: ドローダウン検出、ポジション上限監視、ダッシュボード永続化
- KillSwitch: リスク条件に応じてフラグファイルを書き込み ExecutionEngine 停止をトリガー
- AlertManager: LINE Push を用いたアラート送信（クールダウン付き）
- MonitoringEngine: 上記 Monitor を束ねたポーリングループ（テスト用の run_once もあり）
- Execution 側: BrokerClientFactory を利用したブローカー抽象、OrderManager / Reconciler による再同期機能
- Portfolio: 候補選定（score / equal）、ポジションサイズ計算（リスクベース等）、セクター制限
- Research: Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算
- AI: ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に永続化、マクロセンチメントと ma200 を組み合わせたレジーム判定
- Tools:
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: 監視 DB を可視化する Streamlit アプリ

---

## セットアップ手順

前提:
- Python 3.9+（ソース内での型ヒント等から想定）
- DuckDB、psutil、requests、streamlit、openai など一部サードパーティを使用

1. リポジトリをクローンしてプロジェクトルートへ移動
   - ソースは `src/` 配下にある点に注意

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil requests streamlit openai

   実際のプロジェクトでは requirements.txt または pyproject.toml に依存が定義されている想定なので、そちらを使って下さい。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと、自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 重要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須: J-Quants 用）
     - KABU_API_PASSWORD: （必須: kabuステーション API 用）
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
     - PAPER_FILL_MODE: paper_trading の MockBroker の動作 ("instant" / "partial" / "never" / "reject")（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: Paper 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH, KILL_FLAG_PATH: 実行プロセス PID / kill.flag のパス
   - `.env.example` がある場合はこれを参考に作成してください（コードの Settings._require で未定義時にエラーになるものがあります）。

5. データベース初期化
   - 監視用 SQLite は起動スクリプトが自動で `init_monitoring_db()` を呼び、テーブルを作成します。
   - DuckDB（価格・財務データ等）は事前に prices_daily / raw_financials / raw_news 等のテーブルが用意されている前提です。

---

## 使い方（主要スクリプト）

src 配下を直接実行する場合は `PYTHONPATH=src` を指定するか、パッケージをインストールしてください。

1. 監視ループの起動
   - Purpose: SystemMonitor をポーリングして監視ログを永続化
   - コマンド例:
     - PYTHONPATH=src python -m kabusys.run_monitoring
     - もしくは (開発時) PYTHONPATH=src python src/kabusys/run_monitoring.py
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
   - 備考:
     - 起動直後にプロセス優先度を "high" に設定しようとします（失敗しても継続）。
     - monitoring は常に本番の sqlite_path を使用します（KABUSYS_ENV に関わらず）。

2. 実行エンジン（注文実行）の起動
   - Purpose: ExecutionEngine を起動してセッション実行（発注・リスク管理等）
   - コマンド例:
     - PYTHONPATH=src python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper 用 SQLite（`data/paper_trading.db` 等）を使用して本番 DB と分離します。
     - 起動時に Reconciler を用いて未確定注文の同期等を行います。
     - 起動直後にプロセス優先度を "high" に設定します。

3. Paper Trading 検証レポート
   - Purpose: Paper Trading DB から検証指標を算出して標準出力に表示
   - コマンド例:
     - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - 引数:
       - --from YYYY-MM-DD
       - --to YYYY-MM-DD
       - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数での指定も可）
   - 出力: 稼働率、注文成功率、送信率、レイテンシ統計、PASS/FAIL 判定（デフォルト閾値あり）

4. Streamlit 監視ダッシュボード
   - Purpose: monitoring SQLite を可視化
   - コマンド:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 注意:
     - 監視 DB を読み取り専用で開きます（`?mode=ro`）。MonitoringEngine が動作していないとデータが無い場合があります。

5. AI 関連（ニューススコア / レジーム判定）
   - 関数:
     - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news を OpenAI でスコアリングして ai_scores に書き込む
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — マクロセンチメントと ma200 を合成して market_regime に書き込む
   - 要件:
     - OPENAI_API_KEY を環境変数か引数で与える必要があります（未設定時は ValueError）。

---

## 主な環境変数一覧（抜粋）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（paper_trading 時のモック約定動作）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- SQLITE_PATH: data/monitoring.db（監視用 SQLite）
- DUCKDB_PATH: data/kabusys.duckdb（研究・価格データ）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: data/execution.pid（ExecutionEngine の PID ファイル）
- KILL_FLAG_PATH: data/kill.flag（KillSwitch 用フラグ）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 読み込みと Settings クラス
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — レジーム判定（ma200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（テーブル作成 / CRUD）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照あり)
  - execution_engine.py (参照あり)
  - broker_factory.py (参照あり)
  - ...（ブローカー API 抽象・実装等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- data/ （デフォルトデータディレクトリ、ソース管理外）
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db

（上記はソースに現れている主なファイルを抜粋したものです）

---

## 運用上の注意 / トラブルシューティング

- .env の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を用います。パッケージ配布後は自動検出がスキップされる可能性があるので注意してください。
- Monitoring / Execution 起動時に DB のテーブルは自動で作成・マイグレーションされます（init_monitoring_db）。
- デフォルトでは Monitoring は本番の sqlite_path を参照します。paper_trading を利用する場合は KABUSYS_ENV=paper_trading を設定すると Execution は paper 用 DB を分離して使用します。
- OpenAI 呼び出しはネットワークエラーや 429, 5xx を考慮して指数バックオフでリトライしますが、API キーが未設定だと例外になります。
- プロセス優先度 / CPU affinity の設定はプラットフォーム依存です（psutil を使用）。権限不足なら警告を出してスキップします。
- kill.flag を書き込む KillSwitch の評価は冪等で、既存の flag は上書きしません。ExecutionEngine はこのフラグの存在を検知して安全に停止する設計になっている想定です。

---

## 開発者向けメモ

- 研究系関数（research）や portfolio の関数群は純粋関数として設計されており、外部副作用（DB 書き込み等）を行いません。ユニットテストが書きやすい設計です。
- DuckDB は大量の価格・財務データに対する集計を SQL ベースで行うために採用しています。関数は DuckDB の接続を受け取って SQL を実行します。
- テスト時には OpenAI / requests 等の外部呼び出しをモックする設計（内部の _call_openai_api 等を patch 可能）。

---

README は以上です。必要であれば、導入フロー（.env.example の具体例、Docker / systemd ユニット例、CI 用のコマンドなど）や各モジュールの API ドキュメント（関数引数・戻り値の詳細）も追記できます。どの追加情報が欲しいか教えてください。