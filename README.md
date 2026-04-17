# KabuSys

KabuSys は日本株向けの自動売買システムのリポジトリです。戦略・ポートフォリオ構築・発注エンジン・監視・研究・AI（ニュースセンチメント / レジーム判定）などを含むモジュール群を収録しています。

以下はこのコードベースの概観、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

注意: 本 README はソース内のドキュメント文字列や設定コードを基に作成しています。実際の運用時は .env.example を参照して環境変数を適切に設定してください。

---

## プロジェクト概要

- 日本株の自動売買システム向け基盤ライブラリ。
- 主な責務:
  - 発注エンジン（ExecutionEngine）と OrderManager/OrderRepository による注文管理
  - モニタリング（System / Trade / Risk）とアラート（LINE）
  - ポートフォリオ構築（選定・重み付け・ポジション決定）
  - 研究用ファクター計算（DuckDB上の prices_daily/raw_financials を利用）
  - AI モジュール（ニュースのセンチメント、レジーム判定） — OpenAI API を利用
  - Paper Trading モード（本番 DB と分離された SQLite を使用）

---

## 主な機能一覧

- Execution
  - 発注フロー（OrderManager, Reconciler）
  - Broker クライアント抽象化（実ブローカー / モック切替）
  - 再起動時のリコンシリエーション（ブローカーとローカルの突合）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文（stale）や約定異常（価格乖離）検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクイベント記録
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager: LINE Push 通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 DB の可視化）

- Portfolio（純粋関数群）
  - 候補選定、等配分 / スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - 発注株数計算（リスクベース・等配分・スコアベース）、単元株丸め、aggregate cap

- Research
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等のユーティリティ

- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に書き込み
  - regime_detector: ETF 1321 の MA200 とマクロニュースの LLM スコアを合成して market_regime を生成

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリに移動
   - 推奨ルートはリポジトリのプロジェクトルート（.git や pyproject.toml がある場所）。

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須ライブラリ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例: pip install duckdb psutil requests openai streamlit

   （実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

4. データディレクトリ作成（必要に応じて）
   - デフォルトの DB 等は `data/` 以下に置かれます。例:
     - data/monitoring.db
     - data/paper_trading.db
     - data/kabusys.duckdb
   - 実行スクリプトは必要に応じてファイルを作成しますが、アクセス権に注意してください。

5. 環境変数（最低限の必須項目）
   - 必須:
     - JQUANTS_REFRESH_TOKEN — J-Quants API のトークン（Settings.jquants_refresh_token）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（Settings.kabu_api_password）
   - AI/LLM 機能を使う場合:
     - OPENAI_API_KEY — OpenAI API キー
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — ログレベル（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant/partial/never/reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定だと送信しない）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動的な .env ロードを無効化（1 にすると無効）

   - .env 読み込み順:
     - OS 環境変数 > .env.local > .env（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていない場合に自動読み込み）

6. 初回の DB 初期化
   - 監視機能は起動時に必要なテーブルを作成します（init_monitoring_db）。duckdb は必要に応じてファイルを作成します。

---

## 使い方（主なコマンド）

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（KABUSYS_ENV に依らず本番 sqlite_path を参照する実装になっています）。

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 起動中は data/execution.pid に PID を書く（設定により変更可能）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD — レポート開始日
    - --to YYYY-MM-DD — レポート終了日
    - --db PATH — SQLite DB パス（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 機能（ニューススコア・レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出し（プログラム的に）。呼び出しには OPENAI_API_KEY が必要。
  - OpenAI 呼び出しは失敗時にフォールバックする設計（フェイルセーフ）ですが、APIキー未設定時は例外になります。

停止 / Kill
- run_monitoring / run_execution はプロジェクトルート下の data/stop_requested.flag をチェックして終了します（run_execution は起動中にフラグを検知すると engine.stop() を呼ぶ）。
- KillSwitch（リスク条件に応じて）: data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組みがあります。KillSwitch の flag パスは Settings.kill_flag_path で指定可能。
- KillSwitch を手動で消す（ExecutionEngine 起動前のクリーンアップ）場合:
  - rm data/kill.flag またはプログラム的に KillSwitch.clear() を呼ぶ。

ログレベル
- LOG_LEVEL 環境変数で制御（DEBUG / INFO / WARNING / ERROR / CRITICAL）

プロセス優先度
- 実行スクリプトは起動時に set_process_priority("high") を呼び、可能な限り優先度を上げます（psutil による OS ごとの差分吸収）。権限不足で失敗する場合は警告を出してスキップします。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- PAPER_FILL_MODE — instant | partial | never | reject（Paper Trading のモック約定挙動）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE）用
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）、デフォルト 60
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

例 (.env)
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- KABU_API_PASSWORD=your_kabu_password
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=

---

## ディレクトリ構成（主要ファイルと説明）

（ルートは src/kabusys 下を想定）

- src/kabusys/
  - __init__.py — パッケージ宣言、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor を用いたポーリング監視ループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading モード切替）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト（CLI）
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ書き込みユーティリティ
    - alert_manager.py — LINE Push 通知クライアント（クールダウン管理）
    - monitoring_engine.py — 各 Monitor を束ねてポーリングするエンジン
    - streamlit_dashboard.py — streamlit を使ったダッシュボード（read-only）
  - execution/
    - order_manager.py — 発注の公開 API / ステートマシン外側
    - reconciler.py — 起動時の注文・ポジション突合（自動復旧）
    - order_repository.py — Orders DB 操作（SQLite）  ※（ファイルは抜粋されている想定）
    - ...（broker_factory, execution_engine, risk_manager 等が存在）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み付け
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - position_sizing.py — 発注株数計算（リスク制御、単元丸め、aggregate cap）
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM でスコアリングして ai_scores に書き込むロジック
    - regime_detector.py — ETF MA200 とマクロニュースを組み合わせたレジーム判定
  - data/ — 実行時に使用されるファイル群（DB・フラグ・PID 等）
    - stop_requested.flag — run scripts が参照する停止フラグ
    - kill.flag — KillSwitch が書き込む停止フラグ
    - execution.pid — ExecutionEngine の PID（デフォルト）
    - monitoring.db / paper_trading.db / kabusys.duckdb など

---

## 運用上の注意点 / 実装上のポイント

- Settings（config.py）は .env および OS 環境変数を読み込みます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL に従ってポーリングします。値が不正（整数でない、0 以下など）の場合は 60 秒にフォールバックします。
- 監視（Monitoring）は本番用 sqlite_path を参照する設計（run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する点に注意）。
- run_execution は KABUSYS_ENV=paper_trading の場合、Paper 用専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全に分離します。
- AI（OpenAI）呼び出しはリトライやパース失敗時のフォールバックが組まれており、部分的に失敗しても安全に処理を継続する設計です。ただし API キーは必須です（未設定時は例外になる箇所あり）。
- LINE 通知はトークン/ユーザーID が未設定だと送信をスキップします（ログは残る）。
- process priority / CPU affinity の設定は psutil を用いて OS に依存しつつ実行されます。権限がない場合は警告が出ますが処理は継続します。

---

必要があれば、README に合わせたサンプル .env.example、requirements.txt、起動スクリプト（systemd ユニット例）や運用手順（フェイルオーバー、バックアップ、DB マイグレーション手順）なども作成できます。どの情報を追加したいか教えてください。