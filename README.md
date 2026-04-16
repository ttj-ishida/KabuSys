# KabuSys

日本株向け自動売買システムの内部ライブラリ群・ユーティリティ群です。本リポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、および AI 補助（ニュース NLP / レジーム判定）を含みます。

以下はソースツリー（src/kabusys）に基づく README です。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群の集合です。

- 注文生成→ブローカー送信→状態管理を行う ExecutionEngine（発注ロジック、OrderManager、Reconciler 等）
- システム稼働監視（CPU/メモリ/ディスク、データ鮮度、滞留注文・約定異常、ドローダウン監視）
- アラート送信（LINE Push）
- Paper Trading を分離した検証ワークフロー（専用 SQLite DB）
- ファクター計算・特徴量探索（DuckDB と prices_daily / raw_financials テーブルを利用）
- ニュースの自然言語処理による銘柄別センチメント算出（OpenAI を使用）
- ポートフォリオ構築、ポジションサイズ計算、セクター制約・レジーム乗数の適用
- 各種ツール（Paper Trading 検証レポート、Streamlit 監視ダッシュボード 等）

設計方針は安全性・フェイルセーフ性と「ルックアヘッドバイアス回避」を重視しています（多くのモジュールで datetime.today()/date.today() を直接参照しない等）。

---

## 主な機能一覧

- Execution
  - OrderManager: 注文作成、重複検知、ブローカー同期
  - Reconciler: 再起動後の注文・ポジション再同期間（自動復旧）
  - RiskManager / OrderRepository（DB 連携、リスク制御） ※実装ファイル一部を参照
- Monitoring
  - SystemMonitor: CPU / Memory / Disk / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード upsert
  - MonitoringEngine: 各 Monitor をまとめたポーリングループ
  - AlertManager: LINE へ push 通知（クールダウン管理）
  - KillSwitch: kill.flag を書き込むことで ExecutionEngine に停止シグナルを送信
  - Streamlit ダッシュボード（簡易監視 UI）
- Research / Data
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC（スピアマン）計算、統計サマリー
- AI
  - news_nlp: raw_news から銘柄別センチメントを OpenAI によって算出、ai_scores に格納
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- Portfolio
  - 候補選択、重み計算、セクター制約適用、ポジションサイズ計算（単元丸め・aggregate cap 等）
- Utilities
  - Settings: 環境変数 / .env ロード・検証、環境種別（development/paper_trading/live）
  - process_priority: プロセス優先度 / CPU affinity の設定ユーティリティ
- Tools
  - paper_verification_report: paper_trading DB を対象に運用指標（稼働率・成功率・レイテンシ等）のレポート生成

---

## セットアップ手順（ローカル開発用）

以下は最低限の手順例です。プロジェクトの配布に requirements.txt / pyproject.toml があればそちらを利用してください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定します。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定挙動 ("instant" | "partial" | "never" | "reject")
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH 等（必要に応じて）

   - Settings モジュールは .env/.env.local の自動読み込みを行います（プロジェクトルートの検出に .git または pyproject.toml を使用）。

5. データディレクトリの作成
   - mkdir -p data

6. DB 初期化
   - 監視用 DB（monitoring.db）は Monitoring 起動時に自動でテーブルを作成します。
   - DuckDB として使うデータ（prices_daily 等）は別途 ETL で投入する想定です。

注意: process_priority（高優先度設定）や CPU affinity の変更は権限により失敗することがあります。失敗時はログに警告が出ますが正常継続します。

---

## 使い方（主要スクリプト・コマンド）

ソースがパッケージとしてインポート可能な状態（PYTHONPATH が src を含む）での実行例です。リポジトリ直下で開発している場合は `python -m kabusys.<module>` で実行できます。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 実行動作:
    - process priority を "high" に設定（可能なら）
    - sqlite (Settings.sqlite_path) と DuckDB に接続
    - SystemMonitor を定期実行して system_status 等を記録
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが安全に終了

- 注文実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB (PAPER_TRADING_SQLITE_PATH) に記録（本番 DB と分離）
    - Engine は別スレッドで実行され、stop flag を検知すると停止処理を行います
    - 実行 PID は data/execution.pid（設定による）に書き込まれることがあります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH で paper_trading DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring DB を read-only で開いて情報を表示します

- AI / レジーム判定
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime を呼び出すことで、OpenAI を使った処理を行います（API キー必須）

---

## 環境変数 / 設定の要点

- KABUSYS_ENV: 実行環境（development, paper_trading, live）。 Settings.env で検証される。
- PAPER_FILL_MODE: paper_trading 時の注文約定モード（instant, partial, never, reject）
- DATA / FLAGS:
  - data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ（存在するとループ停止）
  - data/kill.flag: KillSwitch が書き込む停止シグナル（ExecutionEngine 停止用）
  - data/execution.pid: Execution の PID ファイル
- DB:
  - SQLITE_PATH (monitoring db): 監視ログ等（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - DUCKDB_PATH: 戦略/リサーチ用の DuckDB ファイル（デフォルト data/kabusys.duckdb）
- API:
  - OPENAI_API_KEY: OpenAI を利用する機能で必須
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の資格情報
- ロギング:
  - LOG_LEVEL: DEBUG/INFO/… を指定可能（Settings.log_level で検証）

注意: Settings は自動で .env（および .env.local）をプロジェクトルートから読み込む仕組みを持ちますが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化できます。

---

## 停止 / 強制停止の仕組み

- 停止フラグ: data/stop_requested.flag を作成すると run_monitoring / run_execution が検出して安全に終了します。
- KillSwitch: リスク条件（例: ドローダウン超過）で data/kill.flag を書き込み、ExecutionEngine にプロセス停止を促します（Execution 側は kill.flag の有無をチェックして起動時にクリアする設定もあり）。
- PID ファイルの stale 検出: SystemMonitor は execution.pid の整合性をチェックし、存在するがプロセスが無ければ stale と判断して削除・アラートを出します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なディレクトリ / ファイルの概要です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings（環境変数読み込み・検証）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続層（テーブル初期化・CRUD）
    - system_monitor.py — システム状態 / データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込み/管理
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor の統合・ポーリング
    - streamlit_dashboard.py — Streamlit による監視 UI
  - execution/
    - order_manager.py — 注文管理（OrderState マシン外向け API）
    - reconciler.py — 起動時リコンシリエーション（Order / Position 照合）
    - （その他: order_repository, broker_factory などの実装ファイルが想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py — マクロ＋MA200 によるレジーム判定

（上記以外にも execution 側のブローカー API 抽象や order_repository 等の補助モジュールがあります）

---

## 運用上の注意 / FAQ

- DB 分離: Paper Trading（PAPER_TRADING_SQLITE_PATH）と本番監視（SQLITE_PATH）は明確に分離されるよう設計されています。paper_trading モードでは本番 DB を汚さないよう注意してください。
- ルックアヘッド回避: Research / AI コンポーネントはルックアヘッドバイアスを避ける設計がなされています（target_date 未満のデータのみ使用等）。
- OpenAI 利用: API 呼び出しで 429 / 5xx / タイムアウト等はリトライ実装がありますが、API キーの漏洩・料金に注意してください。テスト時は該当関数をモックする想定です。
- 権限: process priority / CPU affinity の設定は OS 権限によって失敗することがあります（ログで警告され、そのままスキップされます）。
- .env の自動読み込み: プロジェクトルートが .git または pyproject.toml によって検出される場合に自動で .env/.env.local が読み込まれます。テスト等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発・拡張ガイド（簡潔）

- 新しい監視チェックを追加するには monitoring/*.py に Monitor を実装し MonitoringEngine に追加します。
- DuckDB を使ったファクター等は research/* に追加し、結果は DuckDB テーブル or Python dict で返す想定です。
- OpenAI 呼び出しはモジュール内でラップされており、テスト時は該当ラッパー関数を patch して外部呼び出しを置き換えてください。

---

この README はリポジトリ内のソースコード（src/kabusys）に基づいて作成しています。実際の運用手順や依存関係は配布パッケージのドキュメント / requirements を必ず参照してください。必要であれば README に手順（デプロイ、サービス化、systemd 例、より詳細な .env.example）を追記します。