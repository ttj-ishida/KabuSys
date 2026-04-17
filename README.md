# KabuSys

KabuSys は日本株向けの自動売買・調査・監視を目的とした軽量な Python コードベースです。本 README はリポジトリ内の主要機能、セットアップ手順、起動方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 注文発行・状態管理（Execution 系）
- 監視（Monitoring）：システム状態、注文の滞留／約定異常、ドローダウン等の監視とログ永続化（SQLite）
- ポートフォリオ構築（Portfolio）：候補選定、重み計算、ポジションサイジング、セクター制約等
- リサーチ（Research）：ファクター計算、将来リターン、IC 計算など（DuckDB を利用）
- AI 支援（AI）：ニュースの NLP スコアリングや市場レジーム判定（OpenAI API）
- 管理ツール：Paper Trading 検証レポート生成、Streamlit ダッシュボード など

設計のポイント：
- DuckDB をデータ分析（prices_daily 等）に使用
- SQLite を監視ログ（monitoring.db）や Paper Trading 用 DB（paper_trading.db）に使用
- 実行時にプロセス優先度を変更して安定性向上を図る（psutil 利用）
- 環境変数 / .env ファイルでの設定読み込みを標準化（kabusys.config.Settings）

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動・セッション管理）
  - Broker クライアントの抽象化（本番／モック切替：KABUSYS_ENV=paper_trading）
  - リコンシリエーション（再起動時の注文・ポジション突合）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス／データ鮮度監視
  - TradeMonitor: 滞留注文（stale order）や約定異常価格の検知
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新、リスクログ記録
  - MonitoringDB: 監視ログの SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - AlertManager: LINE Push による通知（任意）
  - KillSwitch: flag ファイルでの ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（簡易 UI）
- Portfolio
  - 候補選定、等金額・スコア加重配分
  - セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元丸め、aggregate cap）
- Research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI
  - news_nlp: raw_news を LLM（OpenAI）で評価して ai_scores に書き込み
  - regime_detector: ETF の MA200 乖離とマクロニュースを組み合わせてレジーム判定

---

## セットアップ手順

前提
- Python 3.9+ を想定（使用するライブラリに合わせて調整）
- Git リポジトリをクローン済み
- インターネット接続（OpenAI を使う機能を利用する場合）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトによっては追加パッケージが必要になる場合があります）

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 監視や Execution の設定例（デフォルトが使える項目も多い）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
     - PAPER_TRADING_SQLITE_PATH（paper_trading DB を上書き）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知
     - LOG_LEVEL（DEBUG/INFO/...）
   - 例 .env の断片:
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ
   - デフォルトでは `data/` 配下に SQLite / DuckDB ファイルを置く想定です。必要に応じてディレクトリを作成してください。
   - Execution / Monitoring の PID / flag ファイルも `data/` に書き込まれます（例: data/execution.pid, data/kill.flag, data/stop_requested.flag）。

---

## 使い方（主要コマンド）

- 監視ループ起動（SystemMonitor の簡単起動スクリプト）
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor をポーリングし、monitoring DB（settings.sqlite_path）へログを追加します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成するか、Ctrl+C。

- Execution エンジン起動
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を起動します。KABUSYS_ENV が `paper_trading` の場合はモックブローカーを使い、Paper Trading 用 DB（デフォルト data/paper_trading.db）に記録して本番 DB と完全分離します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。実行中は同ファイルを作成するとエンジンを停止します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視用の簡易ダッシュボードを起動します（読み取り専用で SQLite を開く）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 説明: Paper Trading DB（デフォルト data/paper_trading.db）を解析して稼働率・注文成功率・レイテンシ等を出力します。

- AI 関連（ニュース NLP / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をライブラリ API として呼び出すか、必要に応じてスクリプト化して実行します。
  - 必須: OPENAI_API_KEY（引数経由でも渡せる実装箇所あり）
  - 注意: API 呼び出しはレートリミット・エラー時にリトライやフォールバックを実装していますが、キー未設定では失敗します。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用

注意: Settings モジュールはプロジェクトルートの `.env` / `.env.local` を自動ロードします（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 注意事項 / 実運用メモ

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離されるよう設計されています。Paper Trading 用 DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）を使用します。
- run_monitoring / run_execution は stop フラグ（data/stop_requested.flag）をチェックします。ホスト上で停止をトリガーしたい場合はこのファイルを作成してください。
- KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を用いて ExecutionEngine 停止を要求します。KillSwitch は条件を満たすとファイルを書き込みます（冪等）。
- OpenAI を利用する機能は API レート制限・エラー・JSON パース異常への考慮が実装されていますが、API 利用料やレート管理は運用者の責任です。
- プロセス優先度変更（High）や CPU affinity 設定は psutil を用いて実行します。アクセス権限により失敗する場合は警告ログが出ます。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート下の `src/kabusys` を想定）

- src/kabusys/
  - __init__.py               — パッケージ定義、バージョン
  - config.py                 — 環境変数 / 設定管理（Settings）
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートスクリプト
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化・CRUD（MonitoringDB）
    - system_monitor.py       — システム状態 / データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常検知
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — LINE 通知クライアント
    - kill_switch.py          — kill.flag 書き込みロジック
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py        — 注文作成・同期など
    - reconciler.py           — 起動時の注文・ポジションリコンシリエーション
    - （その他 Execution 関連モジュール: broker_factory, execution_engine, order_repository 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数計算（単元丸め・キャップ）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py      — レジーム判定（MA200 + マクロニュース）
  - data/                      — デフォルトの DB / flag / pid ファイル配置を想定
    - monitoring.db (default)
    - paper_trading.db (paper)
    - kabusys.duckdb (default)
    - execution.pid, kill.flag, stop_requested.flag など

---

## 追加情報 / 開発者向け

- Settings（config.py）は .env のパーシングを独自実装しており、quoted value のバックスラッシュエスケープや inline コメント処理などに対応しています。
- MonitoringDB.init_monitoring_db は既存 DB に対する簡易マイグレーション（列追加など）を行います。
- AI モジュールは JSON mode（OpenAI の response_format）を利用し、レスポンスのバリデーション・クリップを行います。
- 研究系関数（research/*）は DuckDB 接続を受け取り SQL ベースで計算します。外部 API には依存しません。

---

もし README に追加したい内容（例: サンプル .env ファイル、具体的なコマンド例や systemd / supervisor 用のユニットファイルテンプレート、テスト実行手順など）があれば教えてください。必要に応じて追記します。